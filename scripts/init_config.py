"""Create private local authentication and empty-cookie runtime settings."""
import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import time


def initialize(root):
    private=Path(root)/'private'
    private.mkdir(mode=0o700,exist_ok=True)
    required=[private/name for name in ('auth_secret.key','token.txt','settings.json')]
    if any(path.exists() for path in required):
        raise SystemExit('Private configuration already exists; nothing was overwritten.')
    secret=secrets.token_bytes(32)
    payload=json.dumps({'create_time':int(time.time()),'project_id':'JoeanAmier/XHS-Downloader'},separators=(',',':'),sort_keys=True).encode()
    encode=lambda value:base64.urlsafe_b64encode(value).rstrip(b'=').decode()
    token=encode(payload)+'.'+encode(hmac.new(secret,payload,hashlib.sha256).digest())
    settings={
        'mapping_data':{},'work_path':'','folder_name':'Download',
        'name_format':'发布时间 作者昵称 作品标题','impersonate':'chrome146',
        'cookie':'','proxy':None,'proxy_download':False,'timeout':10,'avg_delay':6.0,
        'chunk':2097152,'max_retry':1,'record_data':False,'image_format':'JPEG',
        'image_download':True,'video_download':True,'video_cover_download':False,
        'live_download':False,'video_preference':'resolution','folder_mode':False,
        'download_record':False,'author_archive':False,'write_mtime':False,
        'language':'zh_CN','script_server':False,'note_format':'','disclaimer_accepted':True,
    }
    values={'auth_secret.key':secret,'token.txt':(token+'\n').encode(),
            'settings.json':json.dumps(settings,ensure_ascii=False,indent=2).encode()}
    for name,value in values.items():
        with (private/name).open('xb') as file:
            file.write(value)
        os.chmod(private/name,0o600)
    print('Private configuration created. No account cookie or external API key configured.')
    print('Read private/token.txt locally to configure your MCP client; do not publish it.')


if __name__=='__main__':
    os.umask(0o077)
    initialize(Path(__file__).resolve().parents[1])
