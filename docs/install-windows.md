# Windows 安装说明

适合在自己的 Windows 电脑上部署，无需 VPS。本文尚未完成 Windows 实机验证；Windows ARM 设备及全部依赖的兼容性未验证。

## 1. 准备软件和源码

1. 按 [Docker 官方 Windows 安装说明](https://docs.docker.com/desktop/setup/install/windows-install/) 确认系统、内存及虚拟化要求。不要把“所有 Win10 都能用”视为保证，支持范围会随版本更新。
2. 按官方说明启用或安装 WSL 2；如果需要，在管理员 PowerShell 运行 `wsl --install`，按提示重启电脑。已有 WSL 的用户先运行 `wsl --version`，按 Docker 的要求更新。
3. 安装并打开 Docker Desktop，使用 WSL 2 后端和 **Linux containers**；等待引擎启动。本项目不是 Windows 容器。
4. 从 [Python 官方下载页](https://www.python.org/downloads/) 安装 Python 3.12，确保可用 `py -3` 或 `python` 调用。
5. 打开本项目 GitHub 页面 → Code → Download ZIP，解压到普通本地文件夹。私有仓库需要先接受协作者邀请并登录；公开后不需要邀请。不要把生成的 `private/` 同步到云盘。

在解压后的项目文件夹中，右键选择“在终端中打开”，使用 **PowerShell**。执行 `Get-ChildItem`，应能看到 `compose.yaml`、`Dockerfile` 和 `scripts`。

以下步骤在 Windows PowerShell 中执行，不要混用 WSL 内的 Python 或 Linux 命令。

```powershell
docker version
docker compose version
py -3 --version
```

`docker version` 要同时显示 Client 和 Server。如果 `py` 不存在但 `python --version` 返回 Python 3，可把下面的 `py -3` 换成 `python`。如果只弹出商店窗口，请先检查 Python 安装。

## 2. 初始化和启动

阅读 README 的功能限制及内容保存说明后，逐行执行：

```powershell
py -3 scripts/init_config.py
Copy-Item .env.example .env
docker compose config --quiet
docker compose build
docker compose up -d
docker compose ps
```

Windows 先保持 `.env` 中 UID/GID 的默认值，不要执行 Mac/Linux 的 `id` 或 `sed` 命令。首次构建需要下载依赖和约148MB模型，镜像及缓存还会占用额外磁盘；需能访问 GitHub、软件包源及 Hugging Face。

初始化只应执行一次；提示配置已存在时不会覆盖，不要为了重试删除认证文件。后续启动不需要再复制 `.env`，否则会覆盖自己修改的配置。

## 3. 检查并连接 AI

```powershell
py -3 scripts/smoke_mcp.py
```

出现 `MCP smoke check passed` 表示鉴权、5个工具及默认评论数量检查通过，不代表所有公开链接都能读取。失败时等待启动完成后重试，并查看：

```powershell
docker compose ps
docker compose logs --tail=80 reader
```

在同一台电脑的、支持 Streamable HTTP 和自定义鉴权头的 AI 客户端中填写：

| 设置 | 填写内容 |
| --- | --- |
| MCP 类型 | Streamable HTTP |
| 地址 | `http://127.0.0.1:5556/mcp` |
| 鉴权头名称 | `Authorization` |
| 鉴权头值 | `Bearer ` 加上自己 `private/token.txt` 中的完整令牌 |

用记事本打开 `private/token.txt`，只把令牌填进客户端的私密鉴权栏，不要发给别人或截图分享。若客户端单独提供 Bearer Token 输入框，通常只填令牌本身，以客户端说明为准。

先测试公开图文的正文与评论，再测试一个短视频的截图和转录。视频要提交后查询同一个任务 ID。截图需客户端与模型支持图片；页面不提供评论时不能保证读取。MCP 地址不是网页，直接用浏览器打开报错不代表程序失败。

## 4. 手机连接、停止与排错

手机里的 `127.0.0.1` 指手机自身，不会连到电脑。手机 Aru 或由云端发送 MCP 请求的客户端，需要单独配置能到达电脑的安全网络入口、HTTPS 和鉴权。本教程只配置本机访问；不要直接将5556端口暴露到公网。电脑关机、休眠、断网或 Docker 停止后都不可用。

暂停：

```powershell
docker compose stop
```

重新启动：`docker compose up -d`。

- 找不到 Docker 或 Python：安装后重新打开终端，确认程序已正确安装。
- `Cannot connect to the Docker daemon`：先打开 Docker Desktop，确认 WSL 2 与 Linux 容器正常运行。
- 文件挂载或权限错误：确认 `private/` 中已有初始化生成的实际文件，项目路径可被 Docker 访问；不要把密钥改成公开共享，不要关闭安全软件来绕过错误。
- 端口冲突：编辑 `.env` 的 `MCP_PORT` 为未占用端口，重新启动，并同步修改客户端地址。
- 构建下载超时：检查具体失败的下载源与网络，不要关闭证书验证。
- 分享日志前人工删去令牌、私人链接、账号与本机路径；不要上传 `private/`、`.env` 或完整诊断包。

临时媒体会清理，但程序、模型、认证配置和 Docker 缓存仍会保留；客户端聊天记录不由本服务清理。详见 README 的内容保存说明。
