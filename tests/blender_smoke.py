"""Blender integration test: positive review and missing-asset rejection."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--blender',required=True);p.add_argument('--output',required=True,type=Path)
a=p.parse_args();out=a.output.resolve()
if out.exists():raise ValueError('Use a new output directory')
out.mkdir(parents=True)
results=[]
for case in ('valid','missing-image'):
    fixture=out/(case+'-fixture');run=out/(case+'-review')
    command=[a.blender,'--factory-startup','--background','--python-exit-code','1','--python',str(ROOT/'tests/create_fixture.py'),'--',str(fixture)]
    if case=='missing-image':command.append('--missing-image')
    subprocess.run(command,check=True,timeout=120)
    command=[sys.executable,str(ROOT/'scripts/review.py'),'--blender',a.blender,'--input',str(fixture/'fixture.blend'),'--lock',str(fixture/'lock.json'),'--cameras',str(fixture/'cameras.json'),'--features',str(fixture/'features.json'),'--patch',str(fixture/'patch.json'),'--output',str(run),'--width','320','--height','180','--samples','4','--timeout','120']
    result=subprocess.run(command,capture_output=True,text=True,timeout=600)
    report=json.loads((run/'run.json').read_text(encoding='utf8'))
    if case=='valid':
        assert result.returncode==0 and report['ok'],result.stderr
        assert report['changed_objects']==['Fixture building']
        assert len(list(run.glob('before-*.png')))==4 and len(list(run.glob('after-*.png')))==4
        rendered=json.loads((run/'render-before.json').read_text(encoding='utf8'))
        assert len({v['pixel_sha256'] for v in rendered['views']})>1,'Legacy marker overrode review cameras'
        assert all(v['active_camera'].startswith('OTW review camera') for v in rendered['views'])
    else:
        validation=json.loads((run/'validate-before.json').read_text(encoding='utf8'))
        assert result.returncode!=0 and not report['ok']
        assert any('Missing image:' in e for e in validation['errors']),validation
        assert not (run/'review.html').exists()
    results.append({'case':case,'passed':True})
(out/'smoke-results.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf8')
print(json.dumps(results))
