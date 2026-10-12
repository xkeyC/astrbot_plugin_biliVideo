import re
from typing import Optional

import requests


def detect_platform(url: str) -> Optional[str]:
    """
    根据 URL 自动检测视频平台

    :param url: 视频链接
    :return: 平台名称或 None
    """
    url_lower = url.lower()

    if 'bilibili.com' in url_lower or 'b23.tv' in url_lower:
        return 'bilibili'
    elif 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        return 'youtube'
    elif 'douyin.com' in url_lower or 'tiktok.com' in url_lower:
        return 'douyin'

    return None


def extract_video_id(url: str, platform: str) -> Optional[str]:
    """
    从视频链接中提取视频 ID

    :param url: 视频链接
    :param platform: 平台名
    :return: 视频 ID 或 None
    """
    if platform == "bilibili":
        if "b23.tv" in url:
            resolved_url = resolve_bilibili_short_url(url)
            if resolved_url:
                url = resolved_url

        match = re.search(r"BV([0-9A-Za-z]+)", url)
        return f"BV{match.group(1)}" if match else None

    elif platform == "youtube":
        match = re.search(r"(?:v=|youtu\.be/)([0-9A-Za-z_-]{11})", url)
        return match.group(1) if match else None

    elif platform == "douyin":
        match = re.search(r"/video/(\d+)", url)
        return match.group(1) if match else None

    return None


def extract_bilibili_mid(text: str) -> Optional[str]:
    """
    从文本中提取B站用户UID

    支持格式:
    - 纯数字 UID: 12345
    - 空间链接: https://space.bilibili.com/12345
    - 带路径: https://space.bilibili.com/12345/video

    :return: UID 字符串或 None
    """
    text = text.strip()

    if text.isdigit():
        return text

    match = re.search(r"space\.bilibili\.com/(\d+)", text)
    if match:
        return match.group(1)

    return None


# (类型, 正则)，按顺序匹配，第一个命中的生效
_TARGET_PATTERNS = (
    ("video", re.compile(r"(BV[0-9A-Za-z]{10})")),
    ("episode", re.compile(r"(?<![A-Za-z])ep(\d+)", re.I)),
    ("season", re.compile(r"(?<![A-Za-z])ss(\d+)", re.I)),
    ("media", re.compile(r"(?<![A-Za-z])md(\d+)", re.I)),
    ("article", re.compile(r"(?:(?<![A-Za-z])cv|/read/mobile/)(\d+)", re.I)),
    ("audio", re.compile(r"(?<![A-Za-z])au(\d+)", re.I)),
    ("opus", re.compile(r"(?:/opus/|t\.bilibili\.com/|/dynamic/)(\d+)", re.I)),
    ("live", re.compile(r"live\.bilibili\.com/(?:h5/|blanc/)?(\d+)", re.I)),
    ("user", re.compile(r"space\.bilibili\.com/(\d+)", re.I)),
    ("video_aid", re.compile(r"(?<![A-Za-z])av(\d+)", re.I)),
)


def parse_bilibili_target(text: str) -> Optional[tuple]:
    """
    识别 B站资源 ID 或链接（短链需先解析）。

    :return: (kind, id)，kind 为 video/video_aid/episode/season/media/
             article/audio/opus/live/user 之一；无法识别时返回 None
    """
    value = (text or "").strip()
    for kind, pattern in _TARGET_PATTERNS:
        match = pattern.search(value)
        if match:
            return kind, match.group(1)
    return None


def resolve_bilibili_short_url(short_url: str) -> Optional[str]:
    """解析B站短链接"""
    try:
        response = requests.head(short_url, allow_redirects=True, timeout=10)
        return response.url
    except requests.RequestException:
        return None
