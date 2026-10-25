"""Read only comments already embedded in a public mobile share page.

No account, persistent cookies, private comment API or paid service is used.
Public-page approach cross-checked against hazelnutsK/Tidal_Echo-workspace
and help660vip/Yunzai-video-plugin; this module is independently implemented.
"""
import asyncio
import json
import re
import urllib.request
from urllib.parse import urlsplit

from lxml import html

ALLOWED = {'www.xiaohongshu.com','xiaohongshu.com','xhslink.com','xhslink.cn','xhs.link'}
UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1'
LINK = re.compile(r'https?://(?:www\.xiaohongshu\.com|xiaohongshu\.com|xhslink\.com|xhslink\.cn|xhs\.link)/[^\s\"<>【】]+', re.I)

def validate(url):
    parts=urlsplit(url)
    if parts.scheme not in {'http','https'} or parts.hostname not in ALLOWED or parts.username or parts.password or parts.port not in (None,80,443):
        raise ValueError('只支持小红书公开分享链接。')
    return url

class PublicRedirects(urllib.request.HTTPRedirectHandler):
    max_redirections=5
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate(newurl)
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def parse_state(page):
    tree=html.fromstring(page)
    scripts=tree.xpath('//script/text()')
    script=next((s for s in scripts if re.match(r'\s*(?:window\.)?__INITIAL_STATE__\s*=',s)),None)
    if not script:
        return {}
    raw=script.split('=',1)[1].strip().rstrip(';')
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # Replace only unquoted JavaScript literals; do not alter comment strings.
    output=[]
    index=0
    while index<len(raw):
        if raw[index]=='"':
            end=index+1
            while end<len(raw):
                if raw[end]=='\\':
                    end+=2
                elif raw[end]=='"':
                    end+=1
                    break
                else:
                    end+=1
            output.append(raw[index:end]); index=end; continue
        replaced=False
        for old,new in (('new Map([])','[]'),('new Set([])','[]'),('undefined','null'),('NaN','null')):
            if raw.startswith(old,index):
                output.append(new);index+=len(old);replaced=True;break
        if not replaced:
            output.append(raw[index]);index+=1
    return json.loads(''.join(output))

def normalize(row,with_replies=True):
    user=row.get('user') or row.get('userInfo') or {}
    content=row.get('content')
    if not isinstance(content,str):
        return None
    result={'author':str(user.get('nickname') or user.get('nickName') or ''),
            'content':content[:2000],
            'likes':row.get('likeCount',row.get('likeViewCount',row.get('likedCount')))}
    if len(content)>2000: result['content_truncated']=True
    if with_replies:
        children=row.get('subComments') or row.get('sub_comments') or []
        if isinstance(children,list):
            result['visible_replies']=[v for c in children[:3] if isinstance(c,dict) and (v:=normalize(c,False))]
    return result

def fetch_comments(share_text,limit):
    match=LINK.search(share_text)
    if not match:
        return {'status':'invalid_link','comments':[],'message':'未找到受支持的小红书分享链接。'}
    url=validate(match.group().rstrip('。，；！？、.,;!)]}'))
    request=urllib.request.Request(url,headers={
        'User-Agent':UA,'Accept-Language':'zh-CN,zh;q=0.9',
        'Accept':'text/html,application/xhtml+xml,image/*,*/*;q=0.8'})
    opener=urllib.request.build_opener(PublicRedirects())
    with opener.open(request,timeout=20) as response:
        validate(response.url)
        page=response.read(4*1024*1024+1)
        if len(page)>4*1024*1024:
            raise ValueError('分享页面过大，本次未解析。')
    state=parse_state(page)
    holder=state.get('noteData') or {}
    data=holder.get('data') or {}
    note=data.get('noteData') or {}
    rows=(data.get('commentData') or {}).get('comments')
    if not isinstance(rows,list):
        rows=[]
        for entry in (state.get('note',{}).get('noteDetailMap') or {}).values():
            if isinstance(entry,dict):
                candidates=(entry.get('comments') or {}).get('list')
                if isinstance(candidates,list) and candidates:
                    rows=candidates;note=entry.get('note') or {};break
    comments=[c for row in rows[:limit] if isinstance(row,dict) and (c:=normalize(row))]
    return {'status':'ok' if comments else 'unavailable',
            'title':note.get('title'),
            'reported_comment_count':(note.get('interactInfo') or {}).get('commentCount'),
            'returned_count':len(comments),'comments':comments,
            'scope':'仅分享页预载评论及其已提供的少量回复；不是全部评论，不承诺按时间或热度排序。',
            'retention':'页面及评论仅在内存处理，不写文件、不缓存、不下载媒体。',
            'message':'已读取分享页评论。' if comments else '这次分享页没有提供可读取的评论正文，不能据此断定没有评论；不会转入登录或付费方式。'}

def register_comments_tool(server,lock):
    @server.tool(name='get_xhs_comments',description='免登录读取小红书分享页预载的前几条评论正文和已附带的回复，最多20条。支持完整分享文案。不是全部评论；返回unavailable不代表没有评论。无需Cookie、不用账号，不下载或保存内容。',output_schema=None)
    async def get_xhs_comments(url:str,limit:int=20)->dict:
        if not 1<=limit<=20:
            return {'status':'invalid_limit','message':'limit必须为1到20。','comments':[]}
        async with lock:
            try:
                result=await asyncio.to_thread(fetch_comments,url,limit)
            except Exception as exc:
                result={'status':'unavailable','comments':[],'message':str(exc) if isinstance(exc,ValueError) else '分享页请求或解析失败，本次未取得评论正文。'}
            # Small request spacing without retries or anonymous account minting.
            await asyncio.sleep(3)
            return result
