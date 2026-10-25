"""Small ephemeral video-to-MCP bridge; no external model API calls."""
import asyncio
import base64
import json
import secrets
import time
from pathlib import Path

from mcp.types import TextContent, ImageContent

ROOT = Path('/app/Volume/Download')
JOBS = {}
TASKS = set()
TTL = 180

async def command(*args, timeout=40):
    process = await asyncio.create_subprocess_exec(*args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        out, error = await asyncio.wait_for(process.communicate(), timeout)
    except BaseException:
        if process.returncode is None:
            process.kill()
        await process.wait()
        raise
    if process.returncode:
        raise RuntimeError('Media processing failed')
    return out

async def probe(path):
    raw = await command('ffprobe','-v','error','-show_format','-show_streams','-of','json',str(path),timeout=12)
    return json.loads(raw)

def purge():
    now = time.monotonic()
    for key in list(JOBS):
        job = JOBS[key]
        if job['status'] != 'processing' and now - job['finished'] > TTL:
            del JOBS[key]

async def sweep():
    while True:
        await asyncio.sleep(15)
        purge()

def register_video_tools(server, xhs, lock, original, clean_media, silent_output):
    async def worker(job_id, url, frame_count, transcribe_audio):
        job = JOBS[job_id]
        try:
            async with lock:
                clean_media()
                xhs.print.func = silent_output()
                try:
                    async with asyncio.timeout(600):
                        message, data = await original(xhs, url, True, None)
                        if not data:
                            raise ValueError('无法读取此分享链接，可能已失效或被平台限制。')
                        videos = [p for p in ROOT.rglob('*') if p.is_file() and p.suffix.lower() in {'.mp4','.m4v','.mov','.webm','.mkv'}]
                        if len(videos) != 1:
                            raise ValueError('未下载到单个视频；请使用公开视频笔记链接，媒体大小须适合256MB临时区。')
                        video = videos[0]
                        info = await probe(video)
                        duration = float(info.get('format',{}).get('duration',0))
                        if not 0 < duration <= 600:
                            raise ValueError('目前支持10分钟以内的视频；本次未进行部分转录。')
                        frames = []
                        timestamps = [duration * (i + .5) / frame_count for i in range(frame_count)]
                        for i, timestamp in enumerate(timestamps):
                            target = ROOT / f'frame-{i:02d}.jpg'
                            await command('ffmpeg','-nostdin','-v','error','-threads','1','-ss',str(timestamp),'-i',str(video),'-frames:v','1','-vf',"scale='min(960,iw)':-2",'-threads','1','-q:v','4','-y',str(target),timeout=30)
                            image = target.read_bytes()
                            if len(image) > 1024 * 1024:
                                raise ValueError('截图超出返回大小限制。')
                            frames.append((round(timestamp,2), base64.b64encode(image).decode()))
                        transcript = None
                        transcription_error = None
                        has_audio = any(s.get('codec_type') == 'audio' for s in info.get('streams',[]))
                        if transcribe_audio and has_audio:
                            audio = ROOT / 'speech.wav'
                            await command('ffmpeg','-nostdin','-v','error','-threads','1','-i',str(video),'-vn','-ac','1','-ar','16000','-t','600','-y',str(audio),timeout=45)
                            try:
                                transcript = json.loads(await command('python','/app/transcribe_video.py',str(audio),timeout=360))
                            except Exception as exc:
                                transcription_error = type(exc).__name__ + ': 语音转录未完成，不能据此推断视频没有说话。'
                        job.update(status='ready', result={
                            'title': data.get('作品标题'), 'caption': data.get('作品描述'),
                            'author': data.get('作者昵称'), 'duration_seconds': round(duration,2),
                            'frame_times_seconds': [t for t,_ in frames],
                            'transcript': transcript, 'transcription_error': transcription_error,
                            'audio_present': has_audio,
                            'coverage': '画面为均匀采样，可能遗漏帧间动作或文字；语音为自动识别，可能有错字。未读取评论正文。',
                            'media_retention': '原视频、音频与截图文件已在返回结果前删除；结果仅在内存等待领取，领取即移除。',
                        }, frames=frames)
                finally:
                    clean_media()
        except asyncio.CancelledError:
            job.update(status='failed', error='任务已取消。')
            raise
        except Exception as exc:
            message = str(exc) if isinstance(exc, ValueError) else type(exc).__name__ + ': 视频处理未完成，可稍后重新提交。'
            job.update(status='failed', error=message)
        finally:
            job['finished'] = time.monotonic()

    @server.tool(name='read_xhs_video', description='读取小红书视频的画面和语音。用户发来小红书视频链接并希望理解内容时使用。提交后返回job_id；用get_xhs_video_result领取按时间排序的截图和自动语音转录。无账号登录，不读取评论；视频临时下载，处理后删除。', output_schema=None)
    async def read_xhs_video(url: str, frame_count: int = 8, transcribe_audio: bool = True) -> dict:
        purge()
        if not 2 <= frame_count <= 12:
            return {'status':'failed','error':'frame_count 必须在2到12之间。'}
        if any(j['status']=='processing' for j in JOBS.values()):
            return {'status':'busy','message':'已有视频处理中；请先领取现有任务结果，避免重复提交。'}
        if len(JOBS) >= 3:
            return {'status':'busy','message':'请先领取之前的结果，或等待3分钟自动清理。'}
        job_id = secrets.token_urlsafe(18)
        JOBS[job_id] = {'status':'processing','started':time.monotonic()}
        task = asyncio.create_task(worker(job_id,url,frame_count,transcribe_audio))
        TASKS.add(task)
        task.add_done_callback(TASKS.discard)
        return {'status':'processing','job_id':job_id,'next_tool':'get_xhs_video_result','poll_after_seconds':5,'message':'结果完成后仅在内存保留3分钟，领取即移除。'}

    @server.tool(name='get_xhs_video_result', description='领取read_xhs_video的视频理解材料：正文、带时间的语音转录和按顺序排列的实际截图。收到截图后请结合画面和文字分析，不要只看正文。processing时等待5秒再查同一个job_id，不要重复创建任务。结果领取一次后从服务器内存移除；未领取结果3分钟后自动清理。', output_schema=None)
    async def get_xhs_video_result(job_id: str):
        purge()
        job = JOBS.get(job_id)
        if not job:
            return [TextContent(type='text',text=json.dumps({'status':'not_found','message':'任务不存在、已领取或已过期。'},ensure_ascii=False))]
        if job['status']=='processing':
            return [TextContent(type='text',text=json.dumps({'status':'processing','job_id':job_id,'poll_after_seconds':5}))]
        JOBS.pop(job_id)
        if job['status']=='failed':
            return [TextContent(type='text',text=json.dumps({'status':'failed','error':job['error']},ensure_ascii=False))]
        content = [TextContent(type='text',text=json.dumps({'status':'ready',**job['result']},ensure_ascii=False))]
        for timestamp, encoded in job['frames']:
            content.extend([TextContent(type='text',text=f'视频截图，时间 {timestamp:.2f} 秒'), ImageContent(type='image',mimeType='image/jpeg',data=encoded)])
        return content

    task = asyncio.create_task(sweep())
    TASKS.add(task)
    task.add_done_callback(TASKS.discard)
