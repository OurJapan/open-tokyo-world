# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Generate and check a small Before/After without a legacy city scene."""
import argparse
import hashlib
import json
import math
import shutil
import subprocess
import time
from pathlib import Path


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--blender',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--paving-brightness',type=float,default=.85)
    a=p.parse_args()
    if not math.isfinite(a.paving_brightness) or not .5<=a.paving_brightness<=1.5:
        p.error('Paving brightness must be 0.5 to 1.5')
    blender=a.blender.resolve()
    if not blender.is_file():p.error('Blender executable not found')
    out=a.output.resolve()
    out.mkdir(parents=True,exist_ok=False)
    here=Path(__file__).resolve().parent
    root=here.parents[1]
    report={'ok':False,'experiment':'paving brightness only; not a real-world correction',
            'paving_brightness':a.paving_brightness,'runs':{},'source_sha256':{}}
    for f in [here/'scene.py',here/'run.py']+[root/'scripts'/n for n in ('mori_plaza_v1.py','mori_plaza_link_v1.py','mori_entrance_v1.py','mori_terrace_v1.py')]:
        report['source_sha256'][f.relative_to(root).as_posix()]=hashlib.sha256(f.read_bytes()).hexdigest()
    try:
        for label,brightness in [('before',1),('after',a.paving_brightness)]:
            start=time.monotonic()
            for mode in ('build','validate'):
                cmd=[str(blender),'--factory-startup','--background','--disable-autoexec','--python-exit-code','1',
                     '--python',str(here/'scene.py'),'--','--mode',mode,'--output',str(out/label),'--brightness',str(brightness)]
                with (out/f'{label}-{mode}.log').open('w',encoding='utf8') as log:
                    subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
            report['runs'][label]=json.loads((out/label/'validation.json').read_text())
            report['runs'][label]['elapsed_seconds']=round(time.monotonic()-start,3)
        if report['runs']['before']['mesh_fingerprints']!=report['runs']['after']['mesh_fingerprints']:
            raise ValueError('The brightness experiment changed geometry')
        for name in ('ASSET-LICENSE.md','provenance.json'):
            shutil.copyfile(here/name,out/name)
        (out/'review.html').write_text('''<!doctype html><meta charset="utf-8"><title>OurJapan starter review</title>
<style>body{background:#18212a;color:#eee;font:18px sans-serif;max-width:1050px;margin:36px auto;padding:16px}img{width:100%;height:auto}a{color:#9de}section{margin:28px 0}</style>
<h1>OurJapan：6部品の参加用サンプル</h1><p>元の都市ファイルを使わず再生成。舗装の明るさだけを変える操作例です。実物との差分修正ではありません。</p>
<section><h2>Before：サンプルの基準表示</h2><img src="before/preview.png" alt="変更前"></section>
<section><h2>After：舗装の明るさを変更</h2><img src="after/preview.png" alt="変更後"></section>
<p>モデル・プレビュー：© 2026 ark4ez / OurJapan, <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>。配置基盤：PLATEAU港区2025を加工。OSMの参照関係と推定箇所は同梱のprovenance.json・ASSET-LICENSE.mdを参照。</p>''',encoding='utf8')
        report['ok']=True
    except Exception as e:
        report['error']=str(e)
        raise
    finally:
        (out/'run.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__':main()
