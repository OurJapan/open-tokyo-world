# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Package one successful plaza run locally. No upload or Blender execution."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import zipfile

ROOT = Path(__file__).resolve().parents[2]
SOURCES = ('starter/plaza/run.py', 'starter/plaza/scene.py',
           'scripts/mori_plaza_v1.py', 'scripts/mori_plaza_link_v1.py',
           'scripts/mori_entrance_v1.py', 'scripts/mori_terrace_v1.py')
OUTPUTS = ('before/preview.png', 'after/preview.png',
           'before/validation.json', 'after/validation.json',
           'ASSET-LICENSE.md', 'provenance.json')
OBJECTS = {f'OTW Mori {area} / {part}' for area in ('entry plaza', 'plaza link')
           for part in ('paving', 'planters', 'planting')}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n').encode('utf8')


def read_bounded(root, name):
    path = root / name
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('File resolves outside input directory: '+name)
    with path.open('rb') as stream:
        data = stream.read(4_000_001)
    if len(data) > 4_000_000:
        raise ValueError('File exceeds 4 MB: '+name)
    return data


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validation_subset(value, brightness):
    require(value.get('ok') is True and value.get('separate_process_open') is True,
            'Validation did not succeed in a separate process')
    require(value.get('mesh_count') == 6 and value.get('render_pixels') == [800, 600],
            'Not a six-part 800x600 starter run')
    require(value.get('paving_brightness') == brightness, 'Brightness mismatch')
    fingerprints = value.get('mesh_fingerprints', {})
    require(set(fingerprints) == OBJECTS and all(
        isinstance(h, str) and re.fullmatch('[0-9a-f]{64}', h)
        for h in fingerprints.values()), 'Invalid mesh fingerprints')
    version = value.get('blender_version', '')
    require(isinstance(version, str) and re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+(?: LTS)?', version),
            'Invalid Blender version')
    triangles = value.get('triangles')
    require(type(triangles) is int and 0 < triangles < 1_000_000, 'Invalid triangle count')
    return {key: value[key] for key in ('ok', 'separate_process_open', 'mesh_count',
            'render_pixels', 'paving_brightness', 'mesh_fingerprints', 'blender_version', 'triangles')}


def collect(run_dir, root=ROOT):
    """Validate supported evidence and return only explicitly selected bytes."""
    run_dir, root = Path(run_dir).resolve(), Path(root).resolve()
    report = json.loads(read_bounded(run_dir, 'run.json'))
    require(report.get('ok') is True, 'Run did not succeed')
    brightness = report.get('paving_brightness')
    require(type(brightness) in (int, float) and math.isfinite(brightness)
            and .5 <= brightness <= 1.5, 'Invalid brightness')
    require(set(report.get('source_sha256', {})) == set(SOURCES), 'Unexpected source file set')
    require(set(report.get('output_sha256', {})) == set(OUTPUTS),
            'Missing output fingerprints: regenerate with the current run.py')
    files = {}
    for name in SOURCES:
        data = read_bounded(root, name)
        require(digest(data) == report['source_sha256'][name],
                'Source changed since rendering: '+name)
        files['source/'+name] = data
    for name in OUTPUTS:
        data = read_bounded(run_dir, name)
        require(digest(data) == report['output_sha256'][name],
                'Output changed since rendering: '+name)
        if name.endswith('.png'):
            require(len(data) >= 33 and data[:8] == b'\x89PNG\r\n\x1a\n'
                    and data[12:16] == b'IHDR' and struct.unpack('>II', data[16:24]) == (800, 600),
                    'Unexpected PNG header: '+name)
        if name in ('ASSET-LICENSE.md', 'provenance.json'):
            require(data.replace(b'\r\n', b'\n') == read_bounded(
                root, 'starter/plaza/'+name).replace(b'\r\n', b'\n'),
                'Source notice differs from the checked-out starter: '+name)
            files['source/starter/plaza/'+name] = data
        files[name] = data
    validations = {}
    for label, level in [('before', 1), ('after', brightness)]:
        raw = json.loads(files[label+'/validation.json'])
        selected = validation_subset(raw, level)
        require(selected == validation_subset(report.get('runs', {}).get(label, {}), level),
                'Run and validation disagree: '+label)
        validations[label] = selected
        # Never copy arbitrary metadata/log fields into shared evidence.
        files[label+'/validation.json'] = encoded(selected)
    require(validations['before']['mesh_fingerprints'] == validations['after']['mesh_fingerprints'],
            'This packager supports material-only comparisons')
    files['run.json'] = encoded({'ok': True, 'experiment': 'paving brightness only; not a real-world correction',
        'paving_brightness': brightness, 'runs': validations, 'source_sha256': report['source_sha256'],
        'original_output_sha256': report['output_sha256'],
        'note': 'Validation JSON is field-selected; packaged byte hashes are in inventory.json.'})
    for name in ('LICENSE.md', 'MIT-LICENSE.txt', 'NOTICE.md'):
        files['source/'+name] = read_bounded(root, name)
    files['review.html'] = ('''<!doctype html><meta charset="utf-8"><title>OurJapan review package</title>
<style>body{font:18px sans-serif;max-width:960px;margin:32px auto;padding:16px;background:#18212a;color:#eee}img{width:100%}a{color:#9de}</style>
<h1>OurJapan：共有用の比較</h1><p>舗装の明るさだけを変えた練習です。実物との差分修正ではありません。</p>
<h2>Before：1.0</h2><img src="before/preview.png" alt="Before">
<h2>After：''' + str(brightness) + '''</h2><img src="after/preview.png" alt="After">
<p>© 2026 ark4ez / OurJapan — <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>。
配置基盤：PLATEAU港区2025を加工。道路の参照：© OpenStreetMap contributors。
<a href="ASSET-LICENSE.md">利用条件</a> / <a href="provenance.json">出典と推定箇所</a> / <a href="inventory.json">内容一覧</a></p>''').encode('utf8')
    files['README.md'] = (f'''# OurJapan review package

ZIP全体を展開してreview.htmlを開きます。画像、検証結果、出典、利用条件、生成コードを含みます。
変更内容：舗装の明るさ1.0 → {brightness}。形状変更なし。練習であり現実精度の改善ではありません。

再現：sourceフォルダで、PythonとBlenderを用意して実行します。
`python starter/plaza/run.py --blender BLENDER_EXECUTABLE --output build/reproduced --paving-brightness {brightness}`
BLENDER_EXECUTABLEは自分の実行ファイルに置換。参照環境Python 3.12 / Blender 4.5.1 LTS。
source_sha256が実際に使ったコードの版を特定します。再生成したPNGのバイト一致は環境差により保証しません。

validationはレンダリング時の記録です。梱包処理はBlenderを再実行せず、その後のファイル変更をhashで検知します。
記録と画像が一緒に書き換えられた場合を証明する署名や、法的権利・実物精度の自動認定ではありません。
inventory.jsonのSHA-256は梱包したバイト列に対応します。

コード：対象限定MIT（source/LICENSE.md）。独自6部品・プレビュー：CC BY 4.0（ASSET-LICENSE.md）。
第三者の条件とprovenance.jsonを保持してください。生成元コードも入っているので公開前に差分を確認してください。
追加素材・独自コード変更の配布権を自動判定しません。未確認の変更がある場合は共有を保留します。
このパッケージ作成はアップロード・Issue投稿・PR作成を行いません。
''').encode('utf8')
    return files


def package(run_dir, output, root=ROOT):
    files = collect(run_dir, root)
    inventory = {'format_version': 1, 'files': [
        {'path': name, 'bytes': len(data), 'sha256': digest(data)}
        for name, data in sorted(files.items())],
        'excluded': ['blend', 'logs', 'original review.html', 'unlisted files', 'unknown JSON fields'],
        'packager_sha256': digest(Path(__file__).read_bytes()),
        'note': 'inventory.json excludes its own hash; no upload performed'}
    files['inventory.json'] = encoded(inventory)
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    archive = output/'review-package.zip'
    try:
        with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED) as z:
            for name, data in sorted(files.items()):
                info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, data)
        with zipfile.ZipFile(archive) as z:
            require(z.testzip() is None and set(z.namelist()) == set(files), 'ZIP verification failed')
            require(all(z.read(n) == b for n, b in files.items()), 'ZIP bytes differ')
        (output/'inventory.json').write_bytes(files['inventory.json'])
        (output/'README.md').write_bytes(files['README.md'])
        (output/'package-result.json').write_bytes(encoded({'ok': True, 'zip': archive.name,
            'sha256': digest(archive.read_bytes()), 'bytes': archive.stat().st_size,
            'file_count': len(files), 'uploaded': False}))
    except Exception:
        archive.unlink(missing_ok=True)  # Only our newly created archive.
        (output/'package-result.json').write_bytes(encoded({'ok': False, 'uploaded': False}))
        raise
    return archive


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='New directory for ZIP and inventory')
    args = parser.parse_args()
    try:
        print(package(args.run, args.output))
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(1, f'Package not created: {error}\n')
