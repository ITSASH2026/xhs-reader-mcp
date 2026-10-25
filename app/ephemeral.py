"""Run upstream MCP with per-call media disposal and serialized downloads."""
import asyncio
from functools import wraps
from pathlib import Path

from fastmcp import FastMCP
from source import XHS, Settings
from video_reader import register_video_tools
from comments_reader import register_comments_tool
from storage import clean_media

DOWNLOAD = Path('/app/Volume/Download')
lock = asyncio.Lock()
original = XHS.deal_detail_mcp

class SilentOutput:
    def write(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        pass

@wraps(original)
async def ephemeral_call(self, *args, **kwargs):
    async with lock:
        # All upstream components share this Print indirection. Avoid retaining
        # source URLs, note titles or descriptions in container business logs.
        self.print.func = SilentOutput()
        clean_media()
        try:
            return await original(self, *args, **kwargs)
        finally:
            clean_media()

XHS.deal_detail_mcp = ephemeral_call

async def run():
    async with XHS(**Settings().run()) as xhs:
        original_run = FastMCP.run_async
        async def with_video_tools(server, *args, **kwargs):
            register_video_tools(server, xhs, lock, original, clean_media, SilentOutput)
            register_comments_tool(server, lock)
            return await original_run(server, *args, **kwargs)
        FastMCP.run_async = with_video_tools
        await xhs.run_mcp_server()

if __name__ == '__main__':
    asyncio.run(run())
