import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None

ROOT = Path(__file__).resolve().parents[1]

@unittest.skipIf(cv2 is None, 'Install tools/photo_estimation/requirements.txt for image tests')
class PhotoEstimationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location('estimate', ROOT/'tools/photo_estimation/estimate.py')
        cls.e=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.e)

    def metadata(self, image, index):
        encoded=cv2.imencode('.jpg',image)[1].tobytes()
        return {'schema_version':'otw-observation-draft/0.1','client_submission_id':str(index),
          'image':{'width':image.shape[1],'height':image.shape[0],'bytes':len(encoded),'sha256':hashlib.sha256(encoded).hexdigest()},
          'camera_intrinsics':{'status':'calibrated','width':1200,'height':900,'fx':800,'fy':800,'cx':600,'cy':450,'crop':'none','mirrored':False},
          'location':{'latitude':35.7,'longitude':139.74+index*2/(111320*np.cos(np.radians(35.7))),'accuracy_m':.1}},encoded

    def fixture(self):
        rng=np.random.default_rng(42)
        points=np.c_[rng.uniform(-5,5,200),rng.uniform(-3,3,200),rng.uniform(9,20,200)]
        k=np.array([[800.,0,600],[0,800,450],[0,0,1]])
        p1=(points@k.T);p1=p1[:,:2]/p1[:,2:]
        other=points-[2,0,0];p2=other@k.T;p2=p2[:,:2]/p2[:,2:]
        return rng,points,k,p1,p2

    def test_geometry_recovers_known_metric_distance(self):
        _,truth,k,p1,p2=self.fixture()
        points,ids,q=self.e.reconstruct(p1,p2,k,k)
        self.assertGreater(len(points),100)
        np.testing.assert_allclose(points*2,truth[ids],atol=.01)

    def test_rotation_planar_and_low_parallax_fail(self):
        _,truth,k,p1,p2=self.fixture()
        with self.assertRaises(ValueError): self.e.reconstruct(p1,p1,k,k)
        points=truth.copy();points[:,2]=12
        a=points@k.T;a=a[:,:2]/a[:,2:]
        b=(points-[2,0,0])@k.T;b=b[:,:2]/b[:,2:]
        with self.assertRaises(ValueError): self.e.reconstruct(a,b,k,k)

    def test_gps_missing_and_small_baseline_do_not_produce_metres(self):
        a,_=self.metadata(np.zeros((900,1200),np.uint8),0);b,_=self.metadata(np.zeros((900,1200),np.uint8),1)
        self.assertEqual(self.e.gps_scale(a,b)['status'],'provisional')
        b['location']['accuracy_m']=10
        self.assertEqual(self.e.gps_scale(a,b)['status'],'unresolved')
        b['location']=None
        self.assertEqual(self.e.gps_scale(a,b)['reason'],'missing_gps')

    def test_images_zip_to_metric_report_and_hash_rejection(self):
        rng,_,_,p1,p2=self.fixture()
        images=[np.zeros((900,1200),np.uint8) for _ in range(2)]
        for a,b in zip(p1,p2):
            patch=rng.integers(0,256,(17,17),dtype=np.uint8)
            for image,p in zip(images,[a,b]):
                x,y=np.rint(p).astype(int)
                if 10<x<1190 and 10<y<890: image[y-8:y+9,x-8:x+9]=patch
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);paths=[]
            for i,image in enumerate(images):
                d,encoded=self.metadata(image,i);path=root/f'{i}.zip';paths.append(path)
                with zipfile.ZipFile(path,'w') as z:
                    z.writestr('observation.json',json.dumps(d));z.writestr('photo.jpg',encoded)
            result=self.e.run(paths,root/'result')
            self.assertEqual(result['status'],'provisional_metric',result)
            m=result['pairs'][0]['measurement'];self.assertGreater(m['value_m'],1);self.assertLess(m['value_m'],20)
            self.assertFalse(result['automatic_model_changes'])
            self.assertEqual(self.e.run(paths[:1],root/'single')['status'],'unresolved')
            self.assertEqual(self.e.run([paths[0],paths[0]],root/'duplicate')['pairs'][0]['reason'],'duplicate_photo')
            with self.assertRaises(ValueError): self.e.run(paths,root/'result')
            with zipfile.ZipFile(root/'bad.zip','w') as z:
                z.writestr('observation.json',json.dumps(d));z.writestr('photo.jpg',b'broken')
            with self.assertRaisesRegex(ValueError,'hash'):self.e.load_observation(root/'bad.zip')

    def test_blank_images_remain_unresolved(self):
        a=np.zeros((900,1200),np.uint8);b=a.copy();b[0,0]=255
        da,_=self.metadata(a,0);db,_=self.metadata(b,1)
        self.assertEqual(self.e.estimate_pair(da,a,db,b)['status'],'unresolved')

if __name__=='__main__':unittest.main()
