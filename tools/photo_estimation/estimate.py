"""Local two-view photo measurements. Never modifies observations or Blender files."""
import argparse
import hashlib
import itertools
import json
import io
import math
import re
from pathlib import Path
import zipfile

import cv2
import numpy as np
from PIL import Image

VERSION = 'otw-photo-estimation/0.1'


def load_observation(path):
    """Read exact known members, without extracting arbitrary ZIP paths."""
    path = Path(path)
    if path.is_dir():
        meta_path, image_path = path / 'observation.json', path / 'photo.jpg'
        if meta_path.stat().st_size > 1_000_000 or image_path.stat().st_size > 5_000_000:
            raise ValueError('input_too_large')
        metadata, photo = meta_path.read_bytes(), image_path.read_bytes()
    else:
        with zipfile.ZipFile(path) as archive:
            for name, limit in [('observation.json', 1_000_000), ('photo.jpg', 5_000_000)]:
                if archive.namelist().count(name) != 1 or archive.getinfo(name).file_size > limit:
                    raise ValueError('invalid_zip_member: ' + name)
            metadata, photo = archive.read('observation.json'), archive.read('photo.jpg')
    d = json.loads(metadata)
    if d.get('schema_version') != 'otw-observation-draft/0.1':
        raise ValueError('unsupported_observation_schema')
    if not isinstance(d.get('client_submission_id'),str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',d['client_submission_id']):
        raise ValueError('invalid_observation_id')
    spec = d['image']
    if spec['sha256'] != hashlib.sha256(photo).hexdigest() or spec['bytes'] != len(photo):
        raise ValueError('photo_hash_or_size_mismatch')
    if not (0 < spec['width'] <= 4096 and 0 < spec['height'] <= 4096):
        raise ValueError('unsupported_image_dimensions')
    with Image.open(io.BytesIO(photo)) as header:
        if header.format != 'JPEG' or header.size != (spec['width'], spec['height']):
            raise ValueError('jpeg_header_dimensions_mismatch')
    image = cv2.imdecode(np.frombuffer(photo, np.uint8), cv2.IMREAD_GRAYSCALE | cv2.IMREAD_IGNORE_ORIENTATION)
    if image is None or image.shape != (spec['height'], spec['width']):
        raise ValueError('decoded_dimensions_mismatch')
    return d, image


def intrinsics(d):
    c = d.get('camera_intrinsics') or {}
    w, h = d['image']['width'], d['image']['height']
    if c.get('width') != w or c.get('height') != h or c.get('mirrored') is not False or c.get('crop') != 'none':
        raise ValueError('unsupported_camera_geometry')
    # This version supports undistorted calibrated images, or the viewer's FOV assumption.
    if c.get('status') == 'calibrated':
        if any(c.get('distortion', [])):
            raise ValueError('undistorted_images_required')
        fx, fy, cx, cy = [float(c[k]) for k in ('fx', 'fy', 'cx', 'cy')]
    else:
        fov = float(c.get('horizontal_fov_deg', 0))
        if not 15 <= fov <= 120:
            raise ValueError('missing_intrinsics')
        fx = fy = w / (2 * math.tan(math.radians(fov / 2)))
        cx, cy = w / 2, h / 2
    if not all(math.isfinite(x) for x in (fx, fy, cx, cy)) or min(fx, fy) <= 0:
        raise ValueError('invalid_intrinsics')
    return np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1]], dtype=float)


def gps_scale(a, b):
    """Conservative horizontal-baseline screening, not a confidence interval."""
    fixes = [d.get('location') for d in (a, b)]
    if not all(isinstance(f, dict) for f in fixes):
        return {'status': 'unresolved', 'reason': 'missing_gps'}
    for f in fixes:
        if not all(isinstance(f.get(k), (int, float)) and math.isfinite(f[k]) for k in ('latitude', 'longitude', 'accuracy_m')):
            return {'status': 'unresolved', 'reason': 'invalid_gps'}
        if not (-90 <= f['latitude'] <= 90 and -180 <= f['longitude'] <= 180 and 0 < f['accuracy_m'] <= 50):
            return {'status': 'unresolved', 'reason': 'invalid_gps'}
    x, y = fixes
    east = ((y['longitude']-x['longitude']+180) % 360-180)*111320*math.cos(math.radians((x['latitude']+y['latitude'])/2))
    north = (y['latitude']-x['latitude'])*110574
    baseline, error = math.hypot(east, north), x['accuracy_m']+y['accuracy_m']
    if baseline < max(2, 3*error) or baseline > 200:
        return {'status': 'unresolved', 'reason': 'gps_baseline_not_resolved', 'baseline_m': baseline, 'reported_error_sum_m': error}
    return {'status': 'provisional', 'method': 'horizontal_gps_baseline', 'baseline_m': baseline,
            'reported_error_sum_m': error, 'scale_sensitivity_fraction': error/baseline,
            'assumptions': ['camera_centres_at_equal_elevation', 'gps_errors_not_systematically_biased'],
            'accuracy': 'unknown_not_surveyed'}


def reconstruct(p1, p2, k1, k2):
    if len(p1) < 30:
        raise ValueError('too_few_matches')
    n1 = cv2.undistortPoints(np.asarray(p1).reshape(-1, 1, 2), k1, None).reshape(-1, 2)
    n2 = cv2.undistortPoints(np.asarray(p2).reshape(-1, 1, 2), k2, None).reshape(-1, 2)
    focal = min(k1[0, 0], k1[1, 1], k2[0, 0], k2[1, 1])
    cv2.setRNGSeed(17)
    e, mask = cv2.findEssentialMat(n1, n2, np.eye(3), method=cv2.RANSAC, prob=.999, threshold=1.5/focal)
    if e is None or e.shape != (3, 3):
        raise ValueError('essential_matrix_unresolved')
    _, r, t, good = cv2.recoverPose(e, n1, n2, np.eye(3), mask=mask)
    ids = np.flatnonzero(good.ravel())
    if len(ids) < 30 or len(ids)/len(p1) < .35:
        raise ValueError('inconsistent_viewpoints')
    # Pure rotation and predominantly planar scenes leave two-view depth ambiguous.
    _, homography_mask = cv2.findHomography(n1, n2, cv2.RANSAC, 2/focal)
    if homography_mask is not None and homography_mask.mean() > .9:
        raise ValueError('planar_scene_or_rotation_ambiguous')
    a, b = n1[ids], n2[ids]
    homogeneous = cv2.triangulatePoints(np.c_[np.eye(3), np.zeros(3)], np.c_[r, t], a.T, b.T)
    valid = abs(homogeneous[3]) > 1e-10
    ids, a, b, homogeneous = ids[valid], a[valid], b[valid], homogeneous[:, valid]
    points = (homogeneous[:3]/homogeneous[3]).T
    other = points @ r.T + t.ravel()
    reprojection = np.maximum(np.linalg.norm((points[:, :2]/points[:, 2:]-a)*[k1[0,0],k1[1,1]], axis=1), np.linalg.norm((other[:, :2]/other[:, 2:]-b)*[k2[0,0],k2[1,1]], axis=1))
    centre = -r.T @ t.ravel()
    ray1, ray2 = points, points-centre
    angle = np.degrees(np.arccos(np.clip(np.sum(ray1*ray2, axis=1)/(np.linalg.norm(ray1, axis=1)*np.linalg.norm(ray2, axis=1)), -1, 1)))
    keep = np.isfinite(points).all(axis=1) & (points[:, 2] > 0) & (other[:, 2] > 0) & (reprojection <= 2) & (angle >= 1.5)
    points, ids = points[keep], ids[keep]
    if len(points) < 30:
        raise ValueError('insufficient_parallax_or_reprojection_quality')
    return points, ids, {'matched': len(p1), 'triangulated': len(points), 'median_parallax_deg': float(np.median(angle[keep])), 'median_reprojection_px': float(np.median(reprojection[keep]))}


def match_images(a, b):
    sift = cv2.SIFT_create(nfeatures=4000)
    ka, da = sift.detectAndCompute(a, None)
    kb, db = sift.detectAndCompute(b, None)
    if da is None or db is None or min(len(da), len(db)) < 2:
        raise ValueError('insufficient_image_texture')
    matcher = cv2.BFMatcher()
    def ratios(x, y):
        return {m.queryIdx:m.trainIdx for pair in matcher.knnMatch(x, y, k=2) if len(pair)==2 for m,n in [pair] if m.distance < .7*n.distance}
    forward, reverse = ratios(da, db), ratios(db, da)
    pairs = [(i,j) for i,j in forward.items() if reverse.get(j)==i]
    return np.array([ka[i].pt for i,j in pairs], dtype=float), np.array([kb[j].pt for i,j in pairs], dtype=float)


def estimate_pair(a, image_a, b, image_b):
    result = {'observations': [a['client_submission_id'], b['client_submission_id']], 'status': 'unresolved', 'dimension_semantics': 'matched_visible_points_not_building_bounds', 'feature_id': None}
    try:
        if a['image']['sha256'] == b['image']['sha256']:
            raise ValueError('duplicate_photo')
        p1, p2 = match_images(image_a, image_b)
        points, ids, quality = reconstruct(p1, p2, intrinsics(a), intrinsics(b))
        scale = gps_scale(a, b)
        result.update(quality=quality, scale=scale, camera_intrinsics_status=[d['camera_intrinsics']['status'] for d in (a,b)])
        if scale['status'] != 'provisional':
            result['reason'] = scale['reason']
            return result
        points *= scale['baseline_m']
        # Report the distance between two actual reconstructed matches, not an invented object box.
        low, high = np.quantile(points, [.1, .9], axis=0)
        core = np.flatnonzero(((points >= low) & (points <= high)).all(axis=1))
        if len(core) < 10:
            raise ValueError('insufficient_stable_points')
        subset = points[core]
        distances = np.sum((subset[:, None]-subset[None, :])**2, axis=2)
        i, j = np.unravel_index(np.argmax(distances), distances.shape)
        selected = [int(core[i]), int(core[j])]
        result.update(status='provisional_metric', measurement={'name':'visible_matched_point_span', 'value_m':float(np.sqrt(distances[i,j])),
          'accuracy':'unknown', 'endpoints':[{'photo1_xy':p1[ids[v]].tolist(), 'photo2_xy':p2[ids[v]].tolist(), 'camera1_xyz_m':points[v].tolist()} for v in selected]},
          warnings=['No automatic building identification or full building dimensions.', 'GPS scale assumes equal camera elevation.', 'Estimated FOV and uncorrected lens distortion may bias dimensions.', 'Review corresponding pixels before using as a modeling reference.'],
          model_handoff={'apply_automatically':False, 'units':'metre', 'coordinate_frame':'camera1_x_right_y_down_z_forward', 'measurement_only':True})
    except (ValueError, cv2.error) as exc:
        result['reason'] = str(exc)
    return result


def run(inputs, output):
    if not 1 <= len(inputs) <= 12:
        raise ValueError('provide_1_to_12_observation_zips_or_folders')
    output = Path(output)
    if output.exists():
        raise ValueError('output_must_be_new')
    observations = [load_observation(p) for p in inputs]
    report = {'schema_version':VERSION, 'algorithm':'SIFT_mutual_ratio_essential_RANSAC_triangulation_GPS_scale', 'opencv_version':cv2.__version__, 'status':'unresolved',
      'inputs':[{'id':d['client_submission_id'], 'photo_sha256':d['image']['sha256']} for d,_ in observations],
      'pairs':[], 'automatic_model_changes':False}
    if len(observations) < 2:
        report['reason'] = 'at_least_two_overlapping_viewpoints_required'
    annotations=[]
    for index, ((a,ia),(b,ib)) in enumerate(itertools.combinations(observations, 2)):
        pair=estimate_pair(a,ia,b,ib)
        report['pairs'].append(pair)
        if 'measurement' in pair:
            pair['evidence_images']=[]
            for side, image in enumerate((ia,ib), 1):
                marked=cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
                pixels=[tuple(int(round(v)) for v in ep[f'photo{side}_xy']) for ep in pair['measurement']['endpoints']]
                cv2.line(marked, pixels[0], pixels[1], (0,200,255), 2)
                for label, point in zip(('A','B'),pixels):
                    cv2.circle(marked,point,8,(0,0,255),2)
                    cv2.putText(marked,label,point,cv2.FONT_HERSHEY_SIMPLEX,.8,(0,0,255),2)
                name=f'pair-{index+1}-photo-{side}.jpg'
                pair['evidence_images'].append(name)
                annotations.append((name,cv2.imencode('.jpg',marked)[1].tobytes()))
    if any(p['status']=='provisional_metric' for p in report['pairs']):
        report['status']='provisional_metric'
    output.mkdir(parents=True)
    for name, encoded in annotations: (output/name).write_bytes(encoded)
    (output/'estimate.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    lines=['# 写真からの寸法推定', '状態: '+report['status'], '数値は対応する可視点間の暫定推定です。建物全体の寸法ではありません。モデルは変更していません。']
    if report.get('reason'): lines.append(report['reason'])
    for p in report['pairs']:
        lines += [' / '.join(p['observations']), p['status']+': '+p.get('reason','')]
        if 'measurement' in p: lines.append(f"対応点間: {p['measurement']['value_m']:.1f} m（精度不明、確認用）")
        for name in p.get('evidence_images',[]): lines.append(f'![推定した対応点A–B]({name})')
    (output/'report.md').write_text('\n\n'.join(lines)+'\n', encoding='utf-8')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inputs', nargs='+', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args=parser.parse_args()
    try:
        report=run(args.inputs, args.output)
    except (ValueError, TypeError, KeyError, OSError, zipfile.BadZipFile) as exc:
        parser.exit(2, f'Invalid input: {exc}\n')
    print(json.dumps({'status':report['status'], 'report':str(args.output/'estimate.json')}))


if __name__ == '__main__':
    main()
