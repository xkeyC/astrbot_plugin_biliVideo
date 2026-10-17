<div align="center">
  <img src="logo.png" alt="biliVideo" width="100" height="100" style="border-radius: 20px;" />
  <h1>biliVideo 视频总结</h1>
  <p><b>丢个B站链接，AI 帮你秒出精华总结</b></p>

  <br/>

  <img src="https://img.shields.io/badge/version-v1.3.0-blue" />
  <img src="https://img.shields.io/badge/AstrBot-v4.0+-green" />
  <img src="https://img.shields.io/badge/platform-Bilibili-ff69b4" />
  <img src="https://img.shields.io/badge/license-MIT-orange" />
</div>

<br/>

> **🇨🇳 [中文](#-中文文档)** &nbsp;|&nbsp; **🇬🇧 [English](#-english-documentation)**

---

# 🇨🇳 中文文档

## 📖 简介

**biliVideo** 是一款运行在 [AstrBot](https://astrbot.app/) 上的 B站视频总结插件。

你只需要丢一个B站视频链接，插件就会自动下载音频、提取字幕、调用 AI 大模型，生成一份结构化的视频总结 —— 并渲染成精美的暗色主题卡片图片发送到群聊。

不仅如此，你还可以 **订阅 UP 主**，新视频发布时自动推送总结到群里，再也不怕错过喜欢的 UP 的内容了。

## 🏆 biliVideo

| 优势 | 说明 |
|------|------|
| 🎨 **图片渲染输出** | 总结渲染为双栏暗色卡片图片，清晰美观 |
| 📱 **移动端优化** | 支持针对手机阅读优化的大字体紧凑布局 |
| 🧠 **三种总结风格** | 简洁 / 详细 / 专业，适用于不同场景 |
| 📡 **订阅自动推送** | 订阅 UP 主，新视频自动推送总结 |
| 🔍 **多格式输入** | 支持完整链接、短链、BV号、UID、空间链接、UP主昵称 |
| ⏱️ **时间戳标记** | 总结中标注视频对应时间点，便于跳转定位 |
| 🔐 **扫码登录** | 在聊天中扫码登录B站，无需手动填写 Cookie |
| 🛡️ **群聊权限控制** | 支持黑名单 / 白名单模式 |
| 📱 **小程序链接识别** | 群里分享B站小程序/短链自动推送视频信息 |
| 🎙️ **字幕 / ASR 双通道** | 平台字幕优先；无字幕时用必剪公共接口或自部署的 local-multimodal-infra 转写（可跟随 AstrBot 的本地多模态服务设置） |
| 🤖 **Agent 工具** | 向 AstrBot Agent 提供搜索、视频、用户、直播、番剧、专栏、音频、评论等 B站工具 |

## 📦 安装

### 前置要求

- [AstrBot](https://astrbot.app/) v4.0+
- 已在 AstrBot 中配置至少一个 LLM Provider（如 DeepSeek、OpenAI 等），或在插件配置中把 `llm_provider` 设为 `openai_compatible` 并填写自定义 OpenAI 兼容接口

### 步骤

**1. 安装插件**

在 AstrBot 管理面板 → 插件管理 → 上传插件 zip 包

**2. 安装系统依赖**

```bash
# FFmpeg（必须 — 用于音频处理）
apt install -y ffmpeg
```

> **📝 图片输出**：首次使用图片输出功能时，插件会自动安装 Playwright Chromium 浏览器（约 150MB）.

**3. 登录B站**

在聊天中发送：
```
/B站登录
```
用B站 App 扫描弹出的二维码即可。

**4. 开始使用 🎉**
```
/总结 https://www.bilibili.com/video/BV1xx411c7mD
```

## 🔧 命令一览

### 基础命令

| 命令 | 说明 |
|------|------|
| `/总结帮助` | 显示帮助信息和当前登录状态 |
| `/总结 <视频链接>` | 为指定视频生成 AI 总结（已有总结时直接引用） |
| `/重新总结 <视频链接>` | 无视已有总结记录，重新生成 AI 总结 |
| `/最新视频 <UP主>` | 获取 UP 主最新视频并生成总结 |

### 登录管理

| 命令 | 说明 |
|------|------|
| `/B站登录` | 扫码登录 B站 |
| `/B站登出` | 退出B站登录 |

### 订阅管理

| 命令 | 说明 |
|------|------|
| `/订阅 <UP主>` | 订阅 UP 主，新视频自动推送总结 |
| `/取消订阅 <UP主>` | 取消订阅 |
| `/订阅列表` | 查看当前订阅 |
| `/检查更新` | 手动检查 UP 主新视频 |

### 自动识别

| 命令 | 说明 |
|------|------|
| `/识别开关` | 开关B站链接自动识别（群里分享链接自动推送视频信息） |

> **💡 提示**：`<UP主>` 支持多种格式 —— 纯数字 UID、空间链接、或者直接输入 UP 主昵称。

### 推送目标

| 命令 | 说明 |
|------|------|
| `/添加推送群 <群号>` | 将 QQ 群加入推送列表 |
| `/添加推送号 <QQ号>` | 将 QQ 号加入推送列表 |
| `/推送列表` | 查看当前推送目标 |
| `/移除推送 <群号或QQ号>` | 移除推送目标 |

> **💡 提示**：设置推送目标后，所有订阅的新视频总结将**只推送到指定的群/用户**，而不是发起订阅的群。未设置时默认推送到订阅来源群。

### Agent 工具

插件会向 AstrBot Agent 注册以下工具：

| 工具 | 说明 |
|------|------|
| `bilibili_search` | 分类搜索：`video` 视频、`user` 用户/UP主、`live`/`live_room`/`live_user` 直播、`bangumi` 番剧、`movie` 影视、`article` 专栏、`music` 音乐区视频，各类型支持对应的排序方式 |
| `bilibili_get_video_info` | 获取标题、UP主、简介、时长、分P和播放互动数据；`include_comments=true` 时附带评论区（热门/最新，支持翻页，未登录时 B站仅返回前几条） |
| `bilibili_get_video_content` | 提取带时间戳的视频内容；`auto` 优先字幕，`subtitle` 只取字幕，`asr` 强制转写 |
| `bilibili_get_user_info` | 用户资料：昵称、签名、等级、粉丝、投稿数、认证、直播间，可附带最新投稿；支持 UID、空间链接或昵称 |
| `bilibili_get_live_room` | 直播间信息：标题、开播状态与时间、分区、人气、关注数、简介和主播资料；支持房间号（含短号）、直播间链接、`UID:数字` |
| `bilibili_get_bangumi_info` | 番剧/影视详情：简介、评分、播放数据、更新进度、声优与制作人员、分集列表（可翻页）、关联季度；支持 ss/ep/md 号或链接 |
| `bilibili_get_article` | 专栏文章 / 图文动态的元信息与正文（图片以 `[图片]` 占位）；支持 cv 号、专栏链接、opus 和动态链接 |
| `bilibili_get_music` | 音频（au 号）信息与带时间轴的歌词，并给出关联视频的 BV 号 |
| `bilibili_get_comments` | 统一的评论区工具：视频、番剧分集、专栏、图文动态、音频均可，支持热门/最新排序和翻页 |

视频详情、内容和评论工具都接受 BV/av 号、视频链接、番剧分集 ep 号/链接和 b23.tv 短链，番剧与影视分集的字幕/转写同样通过 `bilibili_get_video_content` 获取（大会员专享分集需要登录账号有对应权益，否则只能拿到试看片段）。内容工具默认最多返回 20000 字符，Agent 可通过 `max_chars` 在 1000-50000 之间调整。所有工具与总结命令共用访问控制和 B站登录 Cookie；专栏正文、UP主投稿列表等接口未登录时容易被 B站风控拦截，建议先 `/B站登录`。

当消息通过 `@机器人` 或唤醒关键词触发 LLM，同时又包含 BV 号或 B站链接时，插件会旁路发送视频状态，并继续保留原消息的 AI 对话；开启自动总结时，总结也会在后台并行生成。

### 使用示例

```
/总结 https://www.bilibili.com/video/BV1xx411c7mD
/总结 BV1xx411c7mD
/重新总结 BV1xx411c7mD
/最新视频 某UP主的名字
/订阅 123456789
/添加推送群 123456789
/添加推送号 987654321
/推送列表
/移除推送 123456789
```

## ⚙️ 配置项

在 AstrBot 管理面板 → 插件配置中可设置：

**ASR 与本地多模态服务**

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `asr_provider` | `bcut` | ASR 提供商：`bcut`（必剪公共接口）或 `local_multimodal_infra`（本地多模态服务）。平台字幕始终优先，只有无字幕或 Agent 强制 `source=asr` 时才调用 ASR |
| `local_multimodal_infra_base_url` | `http://127.0.0.1:17890` | local-multimodal-infra Controller 地址，不要包含 `/rpc/infer`；AstrBot 已启用本地多模态服务时忽略此项 |
| `local_multimodal_infra_token` | 空 | 推理 Bearer Token，对应服务端 `LOCAL_MCP_INFER_TOKENS` 中的一个；服务未开启推理鉴权时留空。AstrBot 已启用本地多模态服务时使用那里的令牌 |
| `local_multimodal_infra_model` | `sensevoice-small-onnx` | 本地 ASR 模型，建议使用能返回时间轴的 `sensevoice-small-onnx`；留空时使用 AstrBot 本地多模态服务中“语音识别”选用的模型 |
| `asr_timeout` | `600` | ASR 超时时间（秒，30-1800），音频上传和推理的最长等待时间 |
| `asr_timestamp_granularity_sec` | `10` | 本地 ASR 时间轴目标分段粒度（秒，1-120） |
| `asr_speaker_diarization` | `true` | 本地 ASR 为时间轴片段添加 speaker 标签 |

**LLM**

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `llm_provider` | `astrbot` | `astrbot` 使用 AstrBot 内置 LLM；`openai_compatible` 使用下方自定义 OpenAI 兼容接口 |
| `llm_api_base` | 空 | OpenAI 兼容 API 地址，如 `https://api.openai.com/v1`（插件请求 `{llm_api_base}/chat/completions`） |
| `llm_api_key` | 空 | OpenAI 兼容 API 密钥 |
| `llm_model` | `gpt-4o-mini` | OpenAI 兼容 API 模型名 |

**总结与输出**

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `output_image` | `true` | 总结以图片形式发送；关闭则发送纯文本 |
| `mobile_output` | `false` | 移动端优化输出（更大字体、紧凑布局） |
| `render_timeout` | `60` | 单张图片渲染超时（秒，10-300），超时回退到纯文本 |
| `note_style` | `professional` | 总结风格：`concise` / `detailed` / `professional` |
| `enable_link` | `true` | 在总结中插入原片跳转时间戳 |
| `enable_summary` | `true` | 末尾添加 AI 总结段落 |
| `download_quality` | `fast` | 音频质量：`fast`(32kbps) / `medium`(64kbps) / `slow`(128kbps) |
| `max_note_length` | `3000` | 总结最大字符数（500-10000），超出自动截断 |
| `enable_split_send` | `true` | 总结过长时分段发送；关闭则直接截断 |
| `split_max_length` | `2500` | 分段发送时每段最大字符数（500-4000） |
| `split_by_heading` | `true` | 分段时优先按 `##` 标题切分；关闭则按字符数硬切 |
| `summary_progress_template` | `⏳ 正在生成总结，请稍候（可能需要1-3分钟）...` | 开始生成总结时的提示语 |
| `processing_timeout` | `300` | 配置面板中仍保留此项，当前版本代码未使用 |

**订阅与推送**

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `enable_auto_push` | `false` | 启用定时检查和自动推送新视频总结 |
| `check_interval_minutes` | `600` | 定时检查间隔（分钟，5-1440） |
| `max_subscriptions` | `20` | 每个会话最多订阅的 UP 主数量（1-100） |
| `push_groups` | 空 | 推送 QQ 群列表，英文逗号分隔；也可用 `/添加推送群` 添加 |
| `push_users` | 空 | 推送 QQ 号列表（私聊），英文逗号分隔；也可用 `/添加推送号` 添加 |

**访问控制**

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `access_mode` | `blacklist` | 总结功能（命令与 Agent 工具）的访问控制模式：`blacklist` / `whitelist` |
| `group_list` | 空 | 总结功能的黑/白名单群号，英文逗号分隔 |
| `detect_access_mode` | `blacklist` | B站链接自动识别的访问控制模式：`blacklist` / `whitelist` |
| `detect_group_list` | 空 | 链接识别的黑/白名单群号，英文逗号分隔 |

**链接自动识别**

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `enable_miniapp_detect` | `false` | 自动识别群内B站链接（小程序、卡片、短链等）并推送视频信息；可用 `/识别开关` 实时切换 |
| `detect_show_cover` | `true` | 推送时显示视频封面 |
| `detect_show_uploader` | `true` | 推送时显示UP主名（仅 `video_info_template` 为空时生效） |
| `detect_show_desc` | `true` | 推送时显示视频简介，超 100 字截断（仅 `video_info_template` 为空时生效） |
| `detect_show_pubtime` | `true` | 推送时显示发布时间（仅 `video_info_template` 为空时生效） |
| `detect_show_link` | `true` | 推送时显示完整视频链接（仅 `video_info_template` 为空时生效） |
| `detect_show_stats` | `true` | 推送时显示播放、弹幕、点赞数据（仅 `video_info_template` 为空时生效） |
| `detect_auto_summary` | `false` | 识别链接后自动生成总结（消耗 LLM 额度） |
| `video_info_template` | 见配置面板（非空） | 识别推送的视频信息模板，可用变量 `{title}` `{uploader}` `{desc}` `{pubdate}` `{view}` `{danmaku}` `{like}` `{url}` `{cover}`；非空时上面的 `detect_show_*`（封面除外）不再生效，清空后改用这些开关拼接 |

**其他**

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `debug_mode` | `false` | 启用调试日志 |

## 🎙️ 本地 ASR（local-multimodal-infra）

`asr_provider` 设为 `local_multimodal_infra` 后，无字幕视频会下载为 WAV，通过 `{服务地址}/rpc/infer` 的任务流程转写：`create_task`（`task_kind=asr.transcribe`）→ 签名 URL 上传音频 → `start_task`（`wait=true`），因此可保留 SenseVoice 的时间轴和说话人标签。

服务地址、令牌和模型在**每次转写开始时**确定：

1. **AstrBot 已启用本地多模态服务**（本 fork 的一级设置，WebUI：模型提供商 → 本地多模态服务；英文界面 Providers → Local service）：服务器地址和推理令牌使用 AstrBot 中的设置，插件的 `local_multimodal_infra_base_url` / `local_multimodal_infra_token` 被忽略；`local_multimodal_infra_model` 留空时使用 AstrBot 中“语音识别”选用的模型，有值时以插件配置为准。插件通过 AstrBot 提供给插件的客户端（`Context.get_local_infra()` / `astrbot.api.local_infra`）读取这些设置，修改后下一次转写即生效，无需重载插件。
2. **AstrBot 未启用该服务，或 AstrBot 版本不提供该接口**（例如官方 AstrBot）：使用插件自己的地址、令牌和模型配置。

两处都没有模型时回退到 `sensevoice-small-onnx`。注意 AstrBot 的设置只提供地址、令牌和模型，**不会切换 ASR 提供商**：要使用本地服务，仍需把 `asr_provider` 设为 `local_multimodal_infra`。

## 📋 系统依赖

| 依赖 | 类型 | 用途 |
|------|------|------|
| **FFmpeg** | 系统 | 音频下载处理 (**必须**) |
| **Playwright** | Python | 图片渲染（首次使用图片输出时自动安装 Chromium） |
| yt-dlp | Python | B站视频/音频下载 |
| aiohttp | Python | 异步 HTTP 请求 |
| requests | Python | HTTP 请求 |
| markdown | Python | Markdown → HTML |
| segno | Python | 生成 `/B站登录` 的二维码 |
| latex2mathml | Python | 总结图片中的 LaTeX 公式渲染 |

> **隐私提示**：`bcut` 会把音频上传到必剪公共接口。需要音频始终留在自有环境时，请选择 `local_multimodal_infra`。

> Python 依赖由 AstrBot 在安装插件时按 `requirements.txt` 安装；Playwright Chromium 浏览器会在插件首次使用图片输出时自动安装。

## ⚠️ 注意事项

- 建议首次使用先执行 `/B站登录`：插件不强制登录，但未登录时字幕、评论、投稿列表、专栏正文等接口容易被 B站风控拦截或只返回部分内容
- 需要在 AstrBot 中配置好 LLM Provider（或使用 `llm_provider=openai_compatible` 的自定义接口）
- 视频总结生成约需 1-3 分钟
- 图片渲染失败时会自动回退到纯文本

## 🔎 致谢

本插件的核心总结流程（音频下载、字幕获取、Prompt 构建）参考了 **[BiliNote](https://github.com/JefferyHcool/BiliNote)** (by JefferyHcool)。

B站接口参考了 **[bili-apis](https://github.com/mikufilck/bili-apis)** 整理的 API 文档。

---

# 🇬🇧 English Documentation

## 📖 Introduction

**biliVideo** is an AstrBot plugin that generates AI-powered summaries for Bilibili videos.

Just send a Bilibili video link to your chat, and the plugin will automatically download the audio, extract subtitles, call your configured LLM, and generate a beautifully formatted summary — rendered as a stunning dark-themed card image.

You can also **subscribe to content creators** and receive automatic summary pushes whenever they upload new videos.

## 🏆 biliVideo

| Advantage | Description |
|-----------|-------------|
| 🎨 **Image Rendering** | Summaries rendered as dual-column dark-themed card images |
| 📱 **Mobile Optimized** | Optional mobile-friendly layout with larger fonts and compact design |
| 🧠 **3 Summary Styles** | Concise / Detailed / Professional for different scenarios |
| 📡 **Auto Push** | Subscribe to creators, get summaries pushed automatically |
| 🔍 **Multi-format Input** | Accepts full URLs, short links, BV IDs, UIDs, space links, or creator names |
| ⏱️ **Timestamps** | Key moments marked with video timestamps for quick navigation |
| 🔐 **QR Login** | Login to Bilibili by scanning a QR code in chat |
| 🛡️ **Access Control** | Blacklist / whitelist modes |
| 📱 **Mini-App Detection** | Auto-detect Bilibili links shared in chat and push video info |
| 🎙️ **Subtitles / ASR** | Platform subtitles first; otherwise transcribe with the public Bcut API or a self-hosted local-multimodal-infra (can follow AstrBot's local multimodal service setting) |
| 🤖 **Agent Tools** | Bilibili search, video, user, live, bangumi, article, audio, and comment tools for the AstrBot Agent |

## 📦 Installation

### Prerequisites

- [AstrBot](https://astrbot.app/) v4.0+
- At least one LLM Provider configured in AstrBot (e.g., DeepSeek, OpenAI), or set `llm_provider` to `openai_compatible` and fill in a custom OpenAI-compatible API

### Steps

**1. Install the Plugin**

Upload the plugin zip in AstrBot Admin → Plugin Management → Restart AstrBot

**2. Install System Dependencies**

```bash
# FFmpeg (required — for audio processing)
apt install -y ffmpeg
```

> **📝 Image Output**: Playwright Chromium browser (~150MB) will be auto-installed on first use of image output. No need to manually install wkhtmltopdf.

**3. Login to Bilibili**

Send in chat:
```
/B站登录
```
Scan the QR code with the Bilibili mobile app.

**4. Start Using 🎉**
```
/总结 https://www.bilibili.com/video/BV1xx411c7mD
```

## 🔧 Commands

| Command | Description |
|---------|-------------|
| `/总结帮助` | Show help info and login status |
| `/总结 <video URL>` | Generate AI summary for a video (reuses an existing summary) |
| `/重新总结 <video URL>` | Ignore the existing summary record and generate a new one |
| `/最新视频 <creator>` | Get latest video from a creator and summarize |
| `/B站登录` | QR code login to Bilibili |
| `/B站登出` | Logout from Bilibili |
| `/订阅 <creator>` | Subscribe to a creator for auto push |
| `/取消订阅 <creator>` | Unsubscribe |
| `/订阅列表` | View subscription list |
| `/检查更新` | Manually check for new videos |
| `/添加推送群 <group ID>` | Add a QQ group as push target |
| `/添加推送号 <QQ ID>` | Add a QQ user as push target |
| `/推送列表` | View push targets |
| `/移除推送 <ID>` | Remove a push target |
| `/识别开关` | Toggle auto-detect for Bilibili links |

> **💡 Tip**: `<creator>` accepts numeric UID, space link URL, or creator nickname.
> When push targets are configured, summaries are sent **only** to those targets.

### Agent Tools

| Tool | Description |
|------|-------------|
| `bilibili_search` | Search by type: `video`, `user`, `live`/`live_room`/`live_user`, `bangumi`, `movie`, `article`, `music` (music-zone videos), with per-type ordering |
| `bilibili_get_video_info` | Read metadata, uploader, duration, pages, and statistics; set `include_comments=true` to also fetch comments (hot/latest, paginated; guests only get the first few) |
| `bilibili_get_video_content` | Extract timestamped subtitles or ASR output using `auto`, `subtitle`, or `asr` |
| `bilibili_get_user_info` | User profile (name, bio, level, followers, uploads, verification, live room), optionally with latest uploads; accepts UID, space link, or nickname |
| `bilibili_get_live_room` | Live room info (title, status, start time, area, popularity, followers, description, streamer); accepts room id (short ids too), room link, or `UID:<n>` |
| `bilibili_get_bangumi_info` | Anime/movie/series details: synopsis, rating, stats, progress, cast and staff, paginated episode list, related seasons; accepts ss/ep/md ids or links |
| `bilibili_get_article` | Article (cv) or image-text post (opus) metadata and body text |
| `bilibili_get_music` | Audio track (au) info and timestamped lyrics, plus the linked video BV id |
| `bilibili_get_comments` | Comments for videos, bangumi episodes, articles, posts, and audio tracks (hot/latest, paginated) |

Video tools also accept av ids and bangumi episode (ep) ids/links, so episode subtitles/ASR go through `bilibili_get_video_content`. Article bodies and upload lists are often blocked by Bilibili risk control for guests; log in with `/B站登录` first.

If an `@bot` mention or wake keyword and a Bilibili link occur in the same message, video status is sent as a side response while the normal AI conversation continues.

## ⚙️ Configuration

| Option | Default | Description |
|--------|---------|-------------|
| `asr_provider` | `bcut` | `bcut` (public Bcut API) or `local_multimodal_infra`; platform subtitles always come first, ASR runs only without subtitles or when the Agent forces `source=asr` |
| `local_multimodal_infra_base_url` | `http://127.0.0.1:17890` | local-multimodal-infra Controller URL, without `/rpc/infer`; ignored when AstrBot's local multimodal service is on |
| `local_multimodal_infra_token` | empty | Inference Bearer token (one of the server's `LOCAL_MCP_INFER_TOKENS`); AstrBot's token is used when its local multimodal service is on |
| `local_multimodal_infra_model` | `sensevoice-small-onnx` | Local ASR model ID; when empty, the speech recognition model chosen in AstrBot's local multimodal service is used |
| `asr_timeout` | `600` | ASR timeout in seconds (30-1800) |
| `asr_timestamp_granularity_sec` | `10` | Local ASR timestamp granularity in seconds (1-120) |
| `asr_speaker_diarization` | `true` | Local ASR speaker labels |
| `llm_provider` | `astrbot` | `astrbot` (AstrBot's LLM) or `openai_compatible` |
| `llm_api_base` / `llm_api_key` / `llm_model` | empty / empty / `gpt-4o-mini` | OpenAI-compatible API used when `llm_provider=openai_compatible` |
| `output_image` | `true` | Send summary as image |
| `mobile_output` | `false` | Mobile-optimized output (larger font, compact layout) |
| `render_timeout` | `60` | Per-image render timeout in seconds; falls back to plain text |
| `note_style` | `professional` | Style: `concise` / `detailed` / `professional` |
| `enable_link` | `true` | Insert timestamp jump markers |
| `enable_summary` | `true` | Append an AI summary section |
| `download_quality` | `fast` | Audio quality: `fast` / `medium` / `slow` |
| `max_note_length` | `3000` | Max summary length; longer text is truncated |
| `enable_split_send` / `split_max_length` / `split_by_heading` | `true` / `2500` / `true` | Split long summaries into parts (by `##` headings first) |
| `summary_progress_template` | see panel | Message shown when summarizing starts |
| `processing_timeout` | `300` | Still in the config panel, not used by the current code |
| `enable_auto_push` | `false` | Enable automatic new video push |
| `check_interval_minutes` | `600` | Check interval in minutes (5-1440) |
| `max_subscriptions` | `20` | Max subscriptions per session |
| `push_groups` | empty | Push target QQ groups, comma-separated |
| `push_users` | empty | Push target QQ users, comma-separated |
| `access_mode` / `group_list` | `blacklist` / empty | Access control for summaries (commands and Agent tools) |
| `detect_access_mode` / `detect_group_list` | `blacklist` / empty | Access control for link auto-detection |
| `enable_miniapp_detect` | `false` | Auto-detect Bilibili links in chat (toggle live with `/识别开关`) |
| `detect_show_cover` | `true` | Show video cover in push |
| `detect_show_uploader` / `detect_show_desc` / `detect_show_pubtime` / `detect_show_link` / `detect_show_stats` | `true` | Fields of the pushed info; only used when `video_info_template` is empty |
| `video_info_template` | see panel (non-empty) | Template of the pushed video info (`{title}` `{uploader}` `{desc}` `{pubdate}` `{view}` `{danmaku}` `{like}` `{url}` `{cover}`) |
| `detect_auto_summary` | `false` | Auto-generate summary on link detect |
| `debug_mode` | `false` | Enable debug logging |

## 🎙️ Local ASR (local-multimodal-infra)

With `asr_provider=local_multimodal_infra`, videos without subtitles are downloaded as WAV and transcribed through `{server}/rpc/infer` (`create_task` → signed upload → `start_task`), keeping SenseVoice timestamps and speaker labels.

The server, token, and model are resolved **at the start of each transcription**:

1. **AstrBot's local multimodal service is on** (a first-tier setting of this fork; WebUI: Providers → Local service): the server address and inference token come from AstrBot and the plugin's own address/token are ignored; an empty `local_multimodal_infra_model` uses AstrBot's speech recognition model. The plugin reads this through the client AstrBot gives plugins (`Context.get_local_infra()` / `astrbot.api.local_infra`), so changes apply to the next transcription without reloading.
2. **Otherwise** (service off, or an AstrBot version without it): the plugin's own settings are used.

With no model anywhere, `sensevoice-small-onnx` is used. AstrBot's setting does not switch the ASR provider: `asr_provider` must still be `local_multimodal_infra`.

## 📋 Dependencies

FFmpeg (system, required); Python: playwright, yt-dlp, aiohttp, requests, markdown, segno (login QR code), latex2mathml (formula rendering). Python packages are installed by AstrBot from `requirements.txt`; Playwright Chromium is installed automatically on first image output.

## ⚠️ Notes

- Logging in with `/B站登录` first is recommended: it is not required, but guests are often blocked or get partial results from Bilibili (subtitles, comments, upload lists, article bodies)
- Requires an LLM Provider configured in AstrBot (or `llm_provider=openai_compatible`)
- Summary generation takes ~1-3 minutes per video
- Falls back to plain text if image rendering fails
- `bcut` uploads audio to a public service; select `local_multimodal_infra` to keep ASR in your own environment

## 🔎 Credits

Core summarization flow (audio download, subtitle extraction, prompt building) is based on **[BiliNote](https://github.com/JefferyHcool/BiliNote)** by JefferyHcool.

Bilibili API usage follows the documentation collected in **[bili-apis](https://github.com/mikufilck/bili-apis)**.

---
