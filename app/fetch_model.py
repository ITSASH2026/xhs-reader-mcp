"""Fetch public pinned model files, checking published LFS hashes."""
from pathlib import Path
import hashlib, json, urllib.request

PINNED_REVISION='ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66'
api=f'https://huggingface.co/api/models/Systran/faster-whisper-base/revision/{PINNED_REVISION}?blobs=true'
with urllib.request.urlopen(api,timeout=60) as response:
    metadata=json.load(response)
revision=metadata['sha']
assert revision==PINNED_REVISION, 'Unexpected speech-model revision'
root=Path('/app/models/whisper-base')
root.mkdir(parents=True,exist_ok=True)
manifest={'repository':'Systran/faster-whisper-base','revision':revision,'files':{}}
for sibling in metadata['siblings']:
    name=sibling['rfilename']
    if name not in ('config.json','preprocessor_config.json','model.bin','tokenizer.json') and not name.startswith('vocabulary.'):
        continue
    assert '/' not in name
    request=urllib.request.Request(f'https://huggingface.co/Systran/faster-whisper-base/resolve/{revision}/{name}',headers={'User-Agent':'XHS-video-reader-install'})
    digest=hashlib.sha256()
    size=0
    with urllib.request.urlopen(request,timeout=180) as response, (root/name).open('wb') as target:
        while block:=response.read(1024*1024):
            size+=len(block)
            if size>220*1024*1024:
                raise RuntimeError('Unexpected model file size')
            digest.update(block)
            target.write(block)
    sha=digest.hexdigest()
    expected=sibling.get('lfs',{}).get('sha256')
    if expected and sha!=expected:
        raise RuntimeError('Model SHA256 mismatch')
    manifest['files'][name]={'sha256':sha,'size':size}
assert (root/'model.bin').is_file() and (root/'config.json').is_file()
(root/'manifest.json').write_text(json.dumps(manifest,indent=2))
print('Speech model revision:',revision,'bytes:',sum(v['size'] for v in manifest['files'].values()))
