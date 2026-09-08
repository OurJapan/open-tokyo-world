"""Regenerate Mori from pinned official inputs; never load a legacy scene."""
import argparse, hashlib, json, shutil, subprocess, sys, time, urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'plateau'))
import tile

def bundle_notices(out, here=HERE):
    root=here.parents[1]
    sources={'NOTICE.md':here/'NOTICE.md','ASSET-LICENSE.md':here/'ASSET-LICENSE.md','provenance.json':here/'provenance.json','MIT-LICENSE.txt':root/'MIT-LICENSE.txt','CODE-LICENSE.md':root/'LICENSE.md','PLATEAU-NOTICE.md':here.parent/'plateau/NOTICE.md','PLAZA-LICENSE.md':here.parent/'plaza/ASSET-LICENSE.md','plaza-provenance.json':here.parent/'plaza/provenance.json'}
    # Read all mandatory files first; a missing notice must fail explicitly.
    payload={name:path.read_bytes() for name,path in sources.items()}
    provenance=json.loads(payload['provenance.json'])
    if not provenance.get('license_grant_effective') or not provenance.get('rights_authority_confirmed'):raise ValueError('License consent not recorded')
    if len(provenance['code'])!=11 or len({p['object'] for p in provenance['parts']})!=13:raise ValueError('Incomplete license scope')
    for name,data in payload.items():(out/name).write_bytes(data)
    return {name:hashlib.sha256(data).hexdigest() for name,data in payload.items()}

def validate_part_scope(out):
    scope=json.loads((out/'provenance.json').read_text(encoding='utf8'))
    actual=json.loads((out/'replacement.json').read_text(encoding='utf8'))['parts']
    expected=[p['object'] for p in scope['parts']]
    if len(actual)!=len(expected) or set(actual)!=set(expected):raise ValueError('Generated parts do not match licensed provenance')
    return True

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--blender',required=True,type=Path)
    ap.add_argument('--output',required=True,type=Path)
    ap.add_argument('--inputs',type=Path,help='Explicit directory with both pinned files; otherwise download')
    a=ap.parse_args();out=a.output.resolve();blender=a.blender.resolve()
    if not blender.is_file():ap.error('Blender executable missing')
    out.mkdir(parents=True,exist_ok=False)
    result={'ok':False,'started_at':time.time(),'legacy_scene_used':False,'input_mode':'explicit-pinned-files' if a.inputs else 'official-download'}
    try:
        (out/'inputs').mkdir()
        for name,(url,size,digest) in tile.FILES.items():
            if a.inputs:raw=(a.inputs/name).read_bytes()
            else:
                with urllib.request.urlopen(url,timeout=60) as response:
                    if not response.geturl().startswith('https://'):raise ValueError('Non-HTTPS redirect')
                    raw=response.read(size+1)
            (out/'inputs'/name).write_bytes(tile.verify(name,raw))
        result['notice_sha256']=bundle_notices(out)
        for phase in ['build','before','after']:
            with (out/(phase+'.log')).open('w',encoding='utf8') as log:
                subprocess.run([str(blender),'--factory-startup','--background','--disable-autoexec','--python-exit-code','1','--python',str(HERE/'scene.py'),'--','--folder',str(out),'--phase',phase],stdout=log,stderr=subprocess.STDOUT,timeout=1200,check=True)
            if phase=='build':result['licensed_parts_verified']=validate_part_scope(out)
        result['validation']={p:json.loads((out/(p+'-validation.json')).read_text()) for p in ['before','after']}
        if not all(v['ok'] for v in result['validation'].values()):raise ValueError('Validation failed')
        sections=''.join(f'<h2>{title}</h2><div class="pair"><figure><img src="before-{key}.png"><figcaption>公式PLATEAU＋広場</figcaption></figure><figure><img src="after-{key}.png"><figcaption>独立生成した詳細外装・低層部・入口・テラス</figcaption></figure></div>' for key,title in [('full','全景'),('crown','四隅の頂部と暗いガラス'),('podium','低層部'),('entrance','入口・広場')])
        (out/'review.html').write_text('''<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>森JPタワー独立生成レビュー</title><style>body{background:#17212b;color:#eee;font:17px/1.7 system-ui;margin:32px auto;padding:0 20px;max-width:1400px}h1{font-size:30px}a{color:#9dd9ff}.pair{display:grid;grid-template-columns:1fr 1fr;gap:16px}figure{margin:0}img{width:100%;border-radius:8px}figcaption{font-size:14px}@media(max-width:750px){.pair{grid-template-columns:1fr}}</style><h1>旧都市ファイルなしで森JPタワーを再生成</h1><p>固定した公式PLATEAUデータから断面・低層部を取得し、外装・入口・テラスを生成しました。対象の地物だけを置換し、周囲23地物と広場6部品を保持しています。</p><p>これは公式基盤から詳細モデルへの置換比較です。過去の承認済みモデルとの完全一致を示す比較ではありません。床・天井・屋根の簡略形状を含みますが、家具・屋上設備・道路・地形は含みません。個別建物の底面を揃えた表示座標であり、測量標高ではありません。新しい画像の人間レビューは未完了です。</p>'''+sections+'''<p>出典：<a href="https://www.geospatial.jp/ckan/dataset/plateau-13103-minato-ku-2025">PLATEAU 港区2025</a>を加工。独自広場6部品：ark4ez / OurJapan、CC BY 4.0。森JPタワーの独自追加部分等もCC BY 4.0。元のPLATEAU形状・Textureには提供元の条件が残ります。</p><p><a href="NOTICE.md">出典・許諾範囲</a> / <a href="ASSET-LICENSE.md">独自追加部分のCC BY 4.0</a> / <a href="provenance.json">部品と同意の台帳</a> / <a href="replacement.json">置換記録</a> / <a href="run.json">実行結果</a></p></html>''',encoding='utf8')
        result['ok']=True
    except Exception as exc:
        result['error']=str(exc);raise
    finally:
        root=HERE.parents[1]
        paths=list(HERE.glob('*.py'))+list((HERE.parent/'plateau').glob('*.py'))+[HERE.parent/'plaza/scene.py']+[root/'scripts'/n for n in ['mori_shape.py','mori_crown_v2.py','mori_crown_material.py','mori_facade_v2.py','mori_podium_v3.py','mori_entrance_v1.py','mori_terrace_v1.py','mori_plaza_v1.py','mori_plaza_link_v1.py']]
        result['code_sha256']={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        result['elapsed_seconds']=time.time()-result['started_at']
        result['sources']={n:{'url':x[0],'bytes':x[1],'sha256':x[2]} for n,x in tile.FILES.items()}
        (out/'run.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(out/'review.html')

if __name__=='__main__':main()
