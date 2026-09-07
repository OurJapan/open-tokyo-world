# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Download two pinned public inputs, build, reopen and render in separate processes."""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent))
import tile


def download(name):
    url,size,_=tile.FILES[name]
    with urllib.request.urlopen(url,timeout=60) as response:
        if not response.geturl().startswith('https://'):raise ValueError('Non-HTTPS redirect')
        data=response.read(size+1)
    return tile.verify(name,data)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--blender',required=True,type=Path)
    ap.add_argument('--output',required=True,type=Path)
    args=ap.parse_args()
    blender=args.blender.resolve()
    if not blender.is_file():ap.error('Blender executable not found')
    out=args.output.resolve()
    out.mkdir(parents=True,exist_ok=False)
    here=Path(__file__).resolve().parent
    result={'ok':False,'scope':'one official tile and six plaza parts; legacy-compatible display','started_at_unix':time.time()}
    try:
        (out/'inputs').mkdir()
        for name in tile.FILES:(out/'inputs'/name).write_bytes(download(name))
        for name in ['NOTICE.md'] :shutil.copyfile(here/name,out/name)
        for source,target in [('ASSET-LICENSE.md','PLAZA-LICENSE.md'),('provenance.json','plaza-provenance.json')]:
            shutil.copyfile(here.parent/'plaza'/source,out/target)
        result['sources']={name:{'url':v[0],'bytes':v[1],'sha256':v[2]} for name,v in tile.FILES.items()}
        for phase in ['build','validate']:
            with (out/(phase+'.log')).open('w',encoding='utf8') as log:
                subprocess.run([str(blender),'--factory-startup','--background','--disable-autoexec','--python-exit-code','1','--python',str(here/'scene.py'),'--','--folder',str(out),'--phase',phase],stdout=log,stderr=subprocess.STDOUT,timeout=600,check=True)
        result['validation']=json.loads((out/'validation.json').read_text())
        if not result['validation']['ok']:raise ValueError('Validation failed')
        result['ok']=True
        (out/'review.html').write_text('''<!doctype html><meta charset="utf-8"><title>PLATEAU 1タイル取込試験</title>
<style>body{background:#17212b;color:#eee;font:18px sans-serif;margin:30px auto;max-width:1000px}img{width:100%}a{color:#9cd}</style>
<h1>旧都市ファイルなしの取込試験</h1><p>公式PLATEAU港区2025の24地物＋広場6部品。現実差分のBefore/Afterではなく、再構築と接続の確認です。</p>
<p>建物底面は個別に0.32mへ合わせた旧表示互換モード。測量標高ではありません。森JP本体は公式LOD2.2の形状で、以前修正した詳細モデルではありません。</p>
<h2>全体</h2><img src="overview.png"><h2>入口付近の接続</h2><img src="entrance.png">
<p>出典：<a href="https://www.geospatial.jp/ckan/dataset/plateau-13103-minato-ku-2025">PLATEAU 港区2025</a>を加工して作成（OurJapan）。広場6部品：ark4ez / OurJapan、CC BY 4.0。</p>
<p><a href="NOTICE.md">出典と条件</a> / <a href="PLAZA-LICENSE.md">広場の許諾</a> / <a href="plaza-provenance.json">広場の出典</a> / <a href="georeference.json">地物・元の座標</a> / <a href="validation.json">検証結果</a></p>''',encoding='utf8')
    except Exception as exc:
        result['error']=str(exc)
        raise
    finally:
        root=here.parents[1]
        paths=[*here.glob('*.py'),root/'starter/plaza/scene.py',*[root/'scripts'/n for n in ['mori_plaza_v1.py','mori_plaza_link_v1.py','mori_entrance_v1.py','mori_terrace_v1.py']]]
        result['source_sha256']={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        result['elapsed_seconds']=time.time()-result['started_at_unix']
        (out/'run.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(out/'review.html')


if __name__=='__main__':main()
