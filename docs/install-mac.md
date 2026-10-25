# Mac 安装说明

适合只有 Mac、希望在自己的电脑上运行 MCP 的用户。无需购买 VPS，也无需连接项目维护者的服务器。本文尚未在 Intel Mac 或 Apple 芯片 Mac 上完成实机验证；安装成功与否以最后的检查为准。

## 1. 准备软件和源码

1. 点击左上角苹果菜单 → 关于本机，查看是 Intel 处理器还是 Apple 芯片。
2. 根据 [Docker 官方 Mac 安装说明](https://docs.docker.com/desktop/setup/install/mac-install/) 下载对应的 Docker Desktop，拖入“应用程序”，然后打开，等待引擎启动。系统要求以官方页面为准。
3. 从 [Python 官方下载页](https://www.python.org/downloads/) 安装 Python 3.12；本机只用它生成配置和运行检查脚本。
4. 打开本项目 GitHub 页面 → Code → Download ZIP，解压。私有仓库需要先接受协作者邀请，并登录有权限的 GitHub 账号。公开后则不需要邀请。
5. 建议把项目放在普通本地文件夹，避免云盘同步整个目录，尤其是之后生成的 `private/`。

打开“终端”，输入 `cd `（后面留一个空格），把解压后的项目文件夹拖进终端，按回车。后续命令都在这个目录执行；`ls` 应能看到 `compose.yaml`、`Dockerfile` 和 `scripts`。

依次检查：

```bash
docker version
docker compose version
python3 --version
```

`docker version` 要同时有 Client 和 Server 信息；如果没有 Server，先启动 Docker Desktop。找不到 `python3` 时，先重新打开终端并检查 Python 安装。

## 2. 初始化和启动

先阅读 README 的功能限制和内容保存说明，再逐行执行：

```bash
python3 scripts/init_config.py
cp .env.example .env
```

Mac 的文件所有者通常不是默认的 UID 1000。执行下面命令，将本机用户和组编号写进本项目 `.env`，其余配置保持不变：

```bash
sed -i '' "s/^MCP_UID=.*/MCP_UID=$(id -u)/" .env
sed -i '' "s/^MCP_GID=.*/MCP_GID=$(id -g)/" .env
docker compose config --quiet
docker compose build
docker compose up -d
docker compose ps
```

首次构建会下载程序依赖和约148MB语音模型，完整镜像和构建缓存还会占用额外磁盘，可能需要较长时间。构建需要能访问 GitHub、软件包源及 Hugging Face；此阶段没有使用你的小红书账号。初始化提示已有配置时不要重复生成或删除密钥，继续检查现有配置即可。

### Apple 芯片特别说明

先尝试上面的本机架构构建。部分上游依赖可能缺少 ARM64 安装包，尚未验证全部依赖兼容。如果明确遇到架构或安装包不支持，可以尝试仓库内的 AMD64 模拟运行配置：

```bash
docker compose -f compose.yaml -f examples/compose.amd64.yaml build
docker compose -f compose.yaml -f examples/compose.amd64.yaml up -d
docker compose -f compose.yaml -f examples/compose.amd64.yaml ps
```

这是备用尝试路径，同样未经实机验证，运行和转录可能更慢；如果 Docker 提示需要模拟支持，请按 Docker Desktop 当前官方提示配置。不要把所有构建错误都归因于芯片；下载超时通常需要先检查网络。

## 3. 检查并连接 AI

服务启动后运行：

```bash
python3 scripts/smoke_mcp.py
```

出现 `MCP smoke check passed` 表示鉴权、5个工具和默认评论数量检查通过，尚未验证真实笔记读取。若连接失败，等待启动完成后重试；查看状态和日志：

```bash
docker compose ps
docker compose logs --tail=80 reader
```

在同一台电脑的、支持 Streamable HTTP 和自定义鉴权头的 AI 客户端中添加：

| 设置 | 填写内容 |
| --- | --- |
| MCP 类型 | Streamable HTTP |
| 地址 | `http://127.0.0.1:5556/mcp` |
| 鉴权头名称 | `Authorization` |
| 鉴权头值 | `Bearer ` 加上自己 `private/token.txt` 文件中的完整令牌 |

用本地文本编辑器查看 `private/token.txt`，仅复制到客户端私密鉴权栏；不要截图分享、上传 GitHub 或发给别人。客户端若单独提供 Bearer Token 输入框，通常只填令牌本身，以客户端说明为准。浏览器直接打开 MCP 地址报错不代表安装失败，它不是聊天网页。

先发一条公开图文链接测试标题、正文和页面提供的评论，再发一个短视频测试截图与转录。视频需提交后查询同一个任务 ID；返回图片需要客户端和模型支持图片输入。评论不可用与程序安装失败不同，平台可能没有返回评论。

## 4. 手机连接、停止与排错

`127.0.0.1` 只指向访问者自己的设备；在手机里填这个地址不会连接 Mac。手机 Aru 或云端代发 MCP 请求的客户端，需要能到达 Mac 的安全网络入口、HTTPS 和鉴权；本教程不自动配置公网入口，也不要直接开放5556端口。电脑关机、睡眠、断网或 Docker 停止后服务不可用。

暂停服务：

```bash
docker compose stop
```

重新启动：`docker compose up -d`。若使用了 AMD64 备用配置，启动、停止和查看状态时都要带上同一组 `-f` 参数。

- `Permission denied`：检查 `.env` 的 UID/GID 与 `id -u`、`id -g` 是否一致，且 Docker 获准访问项目文件夹；不要把密钥权限改成所有人可读。
- 端口冲突：在 `.env` 把 `MCP_PORT=5556` 改为未占用端口，重新启动，并同步修改客户端地址。
- 下载失败：检查错误中具体是代码、软件包还是模型源不可达，不要关闭 TLS 证书校验。
- 分享日志前先人工删除私人链接、账号、令牌和本机路径。不要上传 `private/`、`.env` 或完整 Docker 诊断包。

临时视频会在处理后清理，但程序、模型、配置和 Docker 构建缓存会保留；AI聊天记录由客户端自行管理。详见 README 的内容保存说明。
