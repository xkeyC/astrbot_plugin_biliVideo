<div align="center">
  <img src="logo.png" alt="biliVideo" width="100" height="100" style="border-radius: 20px;" />
  <h1>biliVideo 视频总结</h1>
  <p><b>丢个B站链接，AI 帮你秒出精华总结</b></p>

  <br/>

  <img src="https://img.shields.io/badge/version-v1.1.1-blue" />
  <img src="https://img.shields.io/badge/AstrBot-v4.0+-green" />
  <img src="https://img.shields.io/badge/platform-Bilibili-ff69b4" />
  <img src="https://img.shields.io/badge/license-MIT-orange" />
</div>

<br/>

> **🇨🇳 [中文](#-中文文档)** &nbsp;|&nbsp; **🇬🇧 [English](#-english-documentation)**

---

# 🇨🇳 中文文档

## 📖 简介

**biliVideo** 是一款运行在 [AstrBot]((https://astrbot.app/)) 上的 B站视频总结插件。

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

## 📦 安装

### 前置要求

- [AstrBot]((https://astrbot.app/)) v4.0+
- 已配置至少一个 LLM Provider（如 DeepSeek、OpenAI 等）

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
| `bilibili_search_videos` | 按关键词搜索视频，支持综合、播放、最新、弹幕和收藏排序 |
| `bilibili_get_video_info` | 获取标题、UP主、简介、时长、分P和播放互动数据 |
| `bilibili_get_video_content` | 提取带时间戳的视频内容；`auto` 优先字幕，`subtitle` 只取字幕，`asr` 强制转写 |

内容工具默认最多返回 20000 字符，Agent 可通过 `max_chars` 在 1000-50000 之间调整。它与总结命令共用访问控制和 B站登录 Cookie。

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

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `output_image` | `true` | 总结以图片形式发送 |
| `asr_provider` | `bcut` | 无平台字幕时使用 `bcut`（必剪公共接口）或 `local_multimodal_infra` |
| `local_multimodal_infra_base_url` | `http://127.0.0.1:17890` | local-multimodal-infra Controller 地址 |
| `local_multimodal_infra_token` | 空 | 可选推理 Bearer Token，对应服务端 `LOCAL_MCP_INFER_TOKENS` |
| `local_multimodal_infra_model` | `sensevoice-small-onnx` | 本地 ASR 模型 |
| `asr_timestamp_granularity_sec` | `10` | 本地 ASR 时间轴目标粒度 |
| `asr_speaker_diarization` | `true` | 本地 ASR 说话人分离 |
| `mobile_output` | `false` | 移动端优化输出（更大字体、紧凑布局） |
| `note_style` | `professional` | 总结风格：`concise` / `detailed` / `professional` |
| `enable_link` | `true` | 嵌入时间戳标记 |
| `enable_summary` | `true` | 末尾添加 AI 总结段落 |
| `download_quality` | `fast` | 音频质量：`fast` / `medium` / `slow` |
| `enable_auto_push` | `false` | 启用自动推送新视频总结 |
| `check_interval_minutes` | `600` | 定时检查间隔（分钟） |
| `max_subscriptions` | `20` | 每个群最大订阅数 |
| `max_note_length` | `3000` | 总结最大字符数 |
| `push_groups` | 空 | 推送QQ群列表，逗号分隔 |
| `push_users` | 空 | 推送QQ号列表，逗号分隔 |
| `access_mode` | `blacklist` | 群聊访问控制模式 |
| `group_list` | 空 | 群号列表，逗号分隔 |
| `enable_miniapp_detect` | `false` | 自动识别群内B站链接并推送视频信息 |
| `detect_show_cover` | `true` | 推送时显示视频封面 |
| `detect_show_uploader` | `true` | 推送时显示UP主名 |
| `detect_show_desc` | `true` | 推送时显示视频简介 |
| `detect_show_pubtime` | `true` | 推送时显示发布时间 |
| `detect_show_link` | `true` | 推送时显示BV号链接 |
| `detect_show_stats` | `true` | 推送时显示播放量等数据 |
| `detect_auto_summary` | `false` | 识别链接后自动生成总结（消耗LLM额度） |
| `debug_mode` | `false` | 启用调试日志 |

## 📋 系统依赖

| 依赖 | 类型 | 用途 |
|------|------|------|
| **FFmpeg** | 系统 | 音频下载处理 (**必须**) |
| **Playwright** | Python | 图片渲染（首次使用自动安装 Chromium） |
| yt-dlp | Python | B站视频/音频下载 |
| aiohttp | Python | 异步 HTTP 请求 |
| requests | Python | HTTP 请求 |
| markdown | Python | Markdown → HTML |

> **隐私提示**：`bcut` 会把音频上传到必剪公共接口。需要音频始终留在自有环境时，请选择 `local_multimodal_infra`。本地模式使用 `/rpc/infer` 的任务上传链路，因此可保留 SenseVoice 的时间轴和说话人标签。

> Python 依赖和 Playwright Chromium 浏览器会在插件首次使用图片输出时自动安装。

## ⚠️ 注意事项

- 首次使用必须先执行 `/B站登录`
- 需要在 AstrBot 中配置好 LLM Provider
- 视频总结生成约需 1-3 分钟
- 图片渲染失败时会自动回退到纯文本

## 🔎 致谢

本插件的核心总结流程（音频下载、字幕获取、Prompt 构建）参考了 **[BiliNote](https://github.com/JefferyHcool/BiliNote)** (by JefferyHcool)。

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

## 📦 Installation

### Prerequisites

- [AstrBot]((https://astrbot.app/)) v4.0+
- At least one LLM Provider configured (e.g., DeepSeek, OpenAI)

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
| `/总结 <video URL>` | Generate AI summary for a video |
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
| `bilibili_search_videos` | Search videos by keyword with configurable ordering |
| `bilibili_get_video_info` | Read metadata, uploader, duration, pages, and statistics |
| `bilibili_get_video_content` | Extract timestamped subtitles or ASR output using `auto`, `subtitle`, or `asr` |

If an `@bot` mention or wake keyword and a Bilibili link occur in the same message, video status is sent as a side response while the normal AI conversation continues.

## ⚙️ Configuration

| Option | Default | Description |
|--------|---------|-------------|
| `output_image` | `true` | Send summary as image |
| `asr_provider` | `bcut` | Use the public Bcut API or `local_multimodal_infra` when subtitles are unavailable |
| `local_multimodal_infra_base_url` | `http://127.0.0.1:17890` | local-multimodal-infra Controller URL |
| `local_multimodal_infra_token` | empty | Optional inference Bearer token |
| `local_multimodal_infra_model` | `sensevoice-small-onnx` | Local ASR model ID |
| `mobile_output` | `false` | Mobile-optimized output (larger font, compact layout) |
| `note_style` | `professional` | Style: `concise` / `detailed` / `professional` |
| `enable_auto_push` | `false` | Enable automatic new video push |
| `check_interval_minutes` | `600` | Check interval in minutes |
| `max_subscriptions` | `20` | Max subscriptions per group |
| `download_quality` | `fast` | Audio quality: `fast` / `medium` / `slow` |
| `push_groups` | empty | Push target QQ groups, comma-separated |
| `push_users` | empty | Push target QQ users, comma-separated |
| `access_mode` | `blacklist` | Group access control mode |
| `enable_miniapp_detect` | `false` | Auto-detect Bilibili links in chat |
| `detect_show_cover` | `true` | Show video cover in push |
| `detect_show_uploader` | `true` | Show uploader name in push |
| `detect_show_desc` | `true` | Show video description in push |
| `detect_show_pubtime` | `true` | Show publish time in push |
| `detect_show_link` | `true` | Show BV link in push |
| `detect_show_stats` | `true` | Show view/danmaku/like counts |
| `detect_auto_summary` | `false` | Auto-generate summary on link detect |
| `debug_mode` | `false` | Enable debug logging |

## ⚠️ Notes

- Must run `/B站登录` before first use
- Requires an LLM Provider configured in AstrBot
- Summary generation takes ~1-3 minutes per video
- Falls back to plain text if image rendering fails
- `bcut` uploads audio to a public service; select `local_multimodal_infra` to keep ASR in your own environment

## 🔎 Credits

Core summarization flow (audio download, subtitle extraction, prompt building) is based on **[BiliNote](https://github.com/JefferyHcool/BiliNote)** by JefferyHcool.

---
