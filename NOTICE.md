# 来源与第三方说明

本项目是一个小红书公开分享链接阅读扩展，没有得到小红书或下列作者的背书。

本候选版本的二次开发整理日期：2026-10-25。修改范围包括下述上游补丁、MCP 阅读扩展、临时媒体清理与部署模板。

## 内容获取组件

- [JoeanAmier/XHS-Downloader](https://github.com/JoeanAmier/XHS-Downloader)，固定提交 `2ab2620b0dd35b04530e70f1e9c7ab3f78c5d6c5`，GPL-3.0。
- 构建时下载该源码；保留上游源码及 `/app/LICENSE.upstream`，不把其原始功能声称为本项目原创。
- 镜像内显式改动：抑制两处默认访问令牌输出，开启请求证书验证；包装原工具以在调用结束时清理临时媒体。新增评论、截图、转录及异步结果工具，源码位于 `app/`。
- 上游完整源码可由固定提交获取：<https://github.com/JoeanAmier/XHS-Downloader/tree/2ab2620b0dd35b04530e70f1e9c7ab3f78c5d6c5>。

## 评论读取思路参考

实现前对照了以下公开代码对手机分享页预载数据结构的说明，本仓库没有复制其完整应用：

- [hazelnutsK/Tidal_Echo-workspace，backend/xhs.py](https://github.com/hazelnutsK/Tidal_Echo-workspace/blob/main/backend/xhs.py)。
- [help660vip/Yunzai-video-plugin，lib/parsers/xiaohongshu.js](https://github.com/help660vip/Yunzai-video-plugin/blob/main/lib/parsers/xiaohongshu.js)。

本项目评论模块仅解析平台直接返回的JSON，不执行网页脚本、不采集登录Cookie、不使用私有签名API。

## 视频处理组件

- [FFmpeg](https://ffmpeg.org/legal.html)：抽帧和音轨格式转换，具体许可取决于发行版构建选项。
- [SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper)：MIT许可的本地语音转录组件，依赖包保留各自许可。
- [Systran/faster-whisper-base](https://huggingface.co/Systran/faster-whisper-base)：Whisper转换模型，固定revision `ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66`；上游模型卡标注MIT。构建时下载约148MB，记录文件SHA256并核验模型仓库发布的LFS哈希。
- [FastMCP](https://github.com/PrefectHQ/fastmcp) 与 [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)：MCP传输、鉴权与图像内容类型。

仓库不包含模型权重、第三方二进制、用户媒体或登录凭据。发布容器镜像与仅发布源码不同；如另行分发镜像，应同时满足其中全部组件的署名、许可和对应源码义务。

## 发布边界

本源码包没有绑定个人身份、部署主机、域名、账号或真实分享样本。示例使用保留域名 `example.com`，平台及依赖链接仅用于说明公开上游来源。
