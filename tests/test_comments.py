import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
import comments_reader as reader


class CommentsTests(unittest.TestCase):
    def test_js_empty_values_do_not_change_comment_strings(self):
        source={'noteData':{'data':{'commentData':{'comments':[{'content':'keep :undefined and NaN unchanged'}]}}}}
        raw=json.dumps(source)
        page='<script>window.__INITIAL_STATE__='+raw[:-1]+',"empty":undefined,"map":new Map([])}</script>'
        state=reader.parse_state(page)
        self.assertIsNone(state['empty'])
        self.assertEqual(state['map'],[])
        self.assertEqual(state['noteData'],source['noteData'])

    def test_redirect_validation_rejects_external_and_local_targets(self):
        for value in ('http://127.0.0.1/private','https://example.com/',
                      'https://www.xiaohongshu.com.evil.example/',
                      'file:///etc/passwd','https://a:b@www.xiaohongshu.com/explore/test',
                      'https://www.xiaohongshu.com:8000/explore/test'):
            with self.subTest(value=value),self.assertRaises(ValueError):
                reader.validate(value)

    def test_visible_reply_bound_and_long_comment_marker(self):
        result=reader.normalize({'content':'a'*2001,'subComments':[{'content':'reply'}]*5})
        self.assertTrue(result['content_truncated'])
        self.assertEqual(len(result['content']),2000)
        self.assertEqual(len(result['visible_replies']),3)

    def test_page_comment_limit_and_unavailable_are_distinct(self):
        state={'noteData':{'data':{'noteData':{'title':'Fictional fixture'},
            'commentData':{'comments':[{'content':f'Fictional comment {i}'} for i in range(5)]}}}}
        page=('<script>window.__INITIAL_STATE__='+json.dumps(state)+'</script>').encode()
        class Response:
            url='https://www.xiaohongshu.com/explore/EXAMPLE_NOTE_ID'
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,size):return page[:size]
        class Opener:
            def open(self,*args,**kwargs):return Response()
        with patch.object(reader.urllib.request,'build_opener',return_value=Opener()):
            result=reader.fetch_comments(Response.url,2)
            self.assertEqual(result['returned_count'],2)
            state['noteData']['data']['commentData']['comments']=[]
            page=('<script>window.__INITIAL_STATE__='+json.dumps(state)+'</script>').encode()
            self.assertEqual(reader.fetch_comments(Response.url,20)['status'],'unavailable')


if __name__=='__main__':unittest.main()
