"""Build the dependency-free Cloudflare Pages site from the release manifest."""
from pathlib import Path
import argparse
import html
import json
import re
import shutil

ROOT=Path(__file__).resolve().parents[1]
TOOLS_VERSION='1.3.1'
REPO='https://github.com/HiiragiNemu/MagiaExedraTWTools'

def build(output: Path):
    manifest=json.loads((ROOT/'manifests/known-releases.json').read_text(encoding='utf-8'))
    release=next(r for r in manifest['releases'] if r['versionName']==manifest['latestVersion'])
    values={'REPO':REPO,'VERSION':release['versionName'],'CODE':release['versionCode'],'BYTES':release['length'],
            'SIZE_MIB':f"{release['length']/1048576:.1f}",'DATE':manifest['verifiedAt'],'SHA256':release['sha256'],
            'XAPK':manifest['latestEndpoint'],'TOOLS_VERSION':'v'+TOOLS_VERSION,
            'TOOLS_URL':f'{REPO}/releases/download/tw-installer-v{TOOLS_VERSION}/MagiaExedraTWTools-v{TOOLS_VERSION}.zip'}
    output=output.resolve();source=(ROOT/'site').resolve()
    if output==source or output.is_relative_to(source):raise ValueError('Choose a separate output directory')
    output.mkdir(parents=True,exist_ok=True)
    for name in ['style.css','site.js','favicon.svg','_headers']:shutil.copyfile(source/name,output/name)
    template=(source/'index.html').read_text(encoding='utf-8')
    for key,value in values.items():template=template.replace('{{'+key+'}}',html.escape(str(value),quote=True))
    if re.search(r'\{\{[A-Z_]+\}\}',template):raise ValueError('Unresolved template field')
    (output/'index.html').write_text(template,encoding='utf-8',newline='\n')
    (output/'404.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>页面不存在</title><h1>页面不存在</h1><p><a href="/">返回 Exedra 台服下载站</a></p></html>',encoding='utf-8',newline='\n')
    f=output/'files';f.mkdir(exist_ok=True)
    shutil.copyfile(ROOT/f"mobile/SHA256SUMS-tw-{release['versionName']}.txt",f/f"SHA256SUMS-tw-{release['versionName']}.txt")
    shutil.copyfile(ROOT/f"docs/TW_CLIENT_{release['versionName']}_VERIFICATION.json",f/'verification.json')
    shutil.copyfile(ROOT/'manifests/known-releases.json',f/'known-releases.json')
    print(json.dumps({'ok':True,'version':release['versionName'],'output':str(output),'files':9}))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'dist/site')
    build(parser.parse_args().output)
