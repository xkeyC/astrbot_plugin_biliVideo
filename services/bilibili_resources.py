"""
B站分类搜索与各类资源详情：视频、用户、直播间、番剧/影视、专栏/图文、音频。

接口参考 https://github.com/mikufilck/bili-apis
"""

import html
import re
import time
from typing import Dict, List, Optional

from astrbot.api import logger
from .bilibili_api import _strip_search_highlight, request_json

SEARCH_TYPE_URL = "https://api.bilibili.com/x/web-interface/wbi/search/type"

# 工具参数 → B站 search_type
SEARCH_TYPES = {
    "video": "video",
    # B站音频区搜索接口已不再返回结果，改为在音乐分区搜索视频
    "music": "video",
    "user": "bili_user",
    "live": "live",
    "live_room": "live_room",
    "live_user": "live_user",
    "bangumi": "media_bangumi",
    "movie": "media_ft",
    "article": "article",
}
MUSIC_TID = 3

_VIDEO_ORDERS = {"totalrank", "click", "pubdate", "dm", "stow", "scores"}
SEARCH_ORDERS = {
    "video": _VIDEO_ORDERS,
    "music": _VIDEO_ORDERS,
    "article": {"totalrank", "click", "pubdate", "attention", "scores"},
    "live": {"online", "live_time"},
    "live_room": {"online", "live_time"},
    "user": {"0", "fans", "level"},
}

LIVE_STATUS = {0: "未开播", 1: "直播中", 2: "轮播中"}
SEASON_TYPES = {1: "番剧", 2: "电影", 3: "纪录片", 4: "国创", 5: "电视剧", 7: "综艺"}


# ==================== 通用格式化 ====================


def _abs_url(url: str) -> str:
    url = url or ""
    return "https:" + url if url.startswith("//") else url


def _clip(text: str, limit: int) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[:limit] + "…"


def format_ts(value) -> str:
    try:
        value = int(value or 0)
    except (TypeError, ValueError):
        return str(value or "")
    if value <= 0:
        return ""
    if value > 10**11:  # 毫秒
        value //= 1000
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(value))


def html_to_text(value: str) -> str:
    """把专栏/直播间简介的 HTML 转为纯文本，图片替换为 [图片]。"""
    text = re.sub(r"(?is)<(script|style)\b.*?</\1>", "", value or "")
    text = re.sub(r"(?i)<img\b[^>]*>", "[图片]", text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|h[1-6]|li|blockquote|figure|tr|pre)>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text).replace(" ", " ")
    lines = [re.sub(r"[ \t]{2,}", " ", line).strip() for line in text.split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


# ==================== 分类搜索 ====================


def _format_video_result(item: dict) -> Dict:
    bvid = item.get("bvid") or ""
    return {
        "bvid": bvid,
        "title": _strip_search_highlight(item.get("title") or ""),
        "description": _clip(_strip_search_highlight(item.get("description") or ""), 200),
        "author": item.get("author") or "",
        "mid": str(item.get("mid") or ""),
        "category": item.get("typename") or "",
        "duration": item.get("duration") or "",
        "play": item.get("play") or 0,
        "danmaku": item.get("video_review") or 0,
        "favorites": item.get("favorites") or 0,
        "pubdate": format_ts(item.get("pubdate")),
        "pic": _abs_url(item.get("pic") or ""),
        "url": f"https://www.bilibili.com/video/{bvid}",
    }


def _format_user_result(item: dict) -> Dict:
    mid = str(item.get("mid") or "")
    official = item.get("verify_info") or (item.get("official_verify") or {}).get("desc") or ""
    result = {
        "mid": mid,
        "name": _strip_search_highlight(item.get("uname") or ""),
        "sign": _clip(item.get("usign") or "", 120),
        "fans": item.get("fans") or 0,
        "videos": item.get("videos") or 0,
        "level": item.get("level") or 0,
        "official": official,
        "is_live": bool(item.get("is_live")),
        "room_id": item.get("room_id") or 0,
        "url": f"https://space.bilibili.com/{mid}",
    }
    recent = [
        {"bvid": v.get("bvid") or "", "title": v.get("title") or ""}
        for v in (item.get("res") or [])[:3]
        if v.get("bvid")
    ]
    if recent:
        result["recent_videos"] = recent
    return result


def _format_live_room_result(item: dict) -> Dict:
    room_id = item.get("roomid") or item.get("id") or 0
    status = int(item.get("live_status") or 0)
    return {
        "kind": "live_room",
        "room_id": room_id,
        "title": _strip_search_highlight(item.get("title") or ""),
        "uname": _strip_search_highlight(item.get("uname") or ""),
        "uid": str(item.get("uid") or ""),
        "live_status": LIVE_STATUS.get(status, str(status)),
        "online": item.get("online") or 0,
        "area": item.get("cate_name") or "",
        "tags": item.get("tags") or "",
        "live_time": item.get("live_time") if status == 1 else "",
        "url": f"https://live.bilibili.com/{room_id}",
    }


def _format_live_user_result(item: dict) -> Dict:
    room_id = item.get("roomid") or 0
    return {
        "kind": "live_user",
        "uname": _strip_search_highlight(item.get("uname") or ""),
        "uid": str(item.get("uid") or ""),
        "room_id": room_id,
        "is_live": bool(item.get("is_live")),
        "fans": item.get("attentions") or 0,
        "area": item.get("cate_name") or "",
        "tags": item.get("tags") or "",
        "url": f"https://live.bilibili.com/{room_id}",
    }


def _format_media_result(item: dict) -> Dict:
    score = item.get("media_score") or {}
    return {
        "season_id": item.get("season_id") or item.get("pgc_season_id") or 0,
        "media_id": item.get("media_id") or 0,
        "title": _strip_search_highlight(item.get("title") or ""),
        "original_title": _strip_search_highlight(item.get("org_title") or ""),
        "type": item.get("season_type_name") or "",
        "episodes": item.get("index_show") or item.get("ep_size") or "",
        "areas": item.get("areas") or "",
        "styles": item.get("styles") or "",
        "pubdate": format_ts(item.get("pubtime")),
        "score": score.get("score") or None,
        "score_count": score.get("user_count") or 0,
        "description": _clip(item.get("desc") or "", 200),
        "cv": _clip(item.get("cv") or "", 150),
        "url": item.get("url") or item.get("goto_url") or "",
    }


def _format_article_result(item: dict) -> Dict:
    cvid = item.get("id") or 0
    return {
        "article_id": cvid,
        "title": _strip_search_highlight(item.get("title") or ""),
        "author": item.get("author") or "",
        "mid": str(item.get("mid") or ""),
        "category": item.get("category_name") or "",
        "description": _clip(_strip_search_highlight(item.get("desc") or ""), 200),
        "view": item.get("view") or 0,
        "like": item.get("like") or 0,
        "reply": item.get("reply") or 0,
        "pubdate": format_ts(item.get("pub_time")),
        "url": f"https://www.bilibili.com/read/cv{cvid}",
    }


_SEARCH_FORMATTERS = {
    "video": _format_video_result,
    "music": _format_video_result,
    "user": _format_user_result,
    "live_room": _format_live_room_result,
    "live_user": _format_live_user_result,
    "bangumi": _format_media_result,
    "movie": _format_media_result,
    "article": _format_article_result,
}


async def search_by_type(
    keyword: str,
    search_type: str = "video",
    page: int = 1,
    limit: int = 10,
    order: str = "",
    cookies: Optional[dict] = None,
) -> Dict:
    """
    B站分类搜索

    :param search_type: video/music/user/live/live_room/live_user/bangumi/movie/article
    :param order: 排序，取值随类型而定，不支持的值会被忽略
    :return: {"search_type", "page", "total", "num_pages", "results"}
    """
    kind = (search_type or "video").strip().lower()
    if kind not in SEARCH_TYPES:
        raise ValueError(f"search_type 仅支持: {', '.join(SEARCH_TYPES)}")
    keyword = (keyword or "").strip()
    if not keyword:
        raise ValueError("keyword 不能为空")
    page = max(1, int(page))
    limit = min(20, max(1, int(limit)))

    params = {"search_type": SEARCH_TYPES[kind], "keyword": keyword, "page": page}
    if kind == "music":
        params["tids"] = MUSIC_TID
    order = str(order or "").strip()
    if order in SEARCH_ORDERS.get(kind, ()):
        params["order"] = order
        if kind == "user" and order != "0":
            params["order_sort"] = 0

    payload = await request_json(SEARCH_TYPE_URL, params, cookies=cookies, wbi=True)
    data = payload.get("data") or {}
    raw = data.get("result") or []

    if kind == "live":
        raw = raw if isinstance(raw, dict) else {}
        results = [
            _format_live_room_result(item)
            for item in (raw.get("live_room") or [])[:limit]
        ] + [
            _format_live_user_result(item)
            for item in (raw.get("live_user") or [])[:limit]
        ]
        pageinfo = data.get("pageinfo") or {}
        total = sum(
            int((pageinfo.get(key) or {}).get("numResults") or 0)
            for key in ("live_room", "live_user")
        )
    else:
        formatter = _SEARCH_FORMATTERS[kind]
        results = [formatter(item) for item in raw[:limit] if isinstance(item, dict)]
        if kind in {"video", "music"}:
            results = [item for item in results if item["bvid"]]
        total = data.get("numResults") or 0

    return {
        "search_type": kind,
        "page": page,
        "total": total,
        "num_pages": data.get("numPages") or 0,
        "results": results,
    }


async def get_bvid_by_aid(aid: int, cookies: Optional[dict] = None) -> str:
    """av 号转 BV 号"""
    payload = await request_json(
        "https://api.bilibili.com/x/web-interface/view",
        {"aid": int(aid)},
        cookies=cookies,
    )
    bvid = (payload.get("data") or {}).get("bvid") or ""
    if not bvid:
        raise RuntimeError(f"未找到视频 av{aid}")
    return bvid


# ==================== 用户 ====================


async def get_user_card(mid: str, cookies: Optional[dict] = None) -> Dict:
    """用户名片：昵称、签名、粉丝、投稿数、认证等"""
    payload = await request_json(
        "https://api.bilibili.com/x/web-interface/card",
        {"mid": mid, "photo": "false"},
        cookies=cookies,
    )
    data = payload.get("data") or {}
    card = data.get("card") or {}
    if not card:
        raise RuntimeError(f"未找到用户 {mid}")
    official = (card.get("Official") or {}).get("title") or (
        card.get("official_verify") or {}
    ).get("desc") or ""
    vip = ((card.get("vip") or {}).get("label") or {}).get("text") or ""
    mid = str(card.get("mid") or mid)
    return {
        "mid": mid,
        "name": card.get("name") or "",
        "sex": card.get("sex") or "",
        "sign": card.get("sign") or "",
        "level": (card.get("level_info") or {}).get("current_level") or 0,
        "face": card.get("face") or "",
        "fans": data.get("follower") or card.get("fans") or 0,
        "following": card.get("attention") or 0,
        "videos": data.get("archive_count") or 0,
        "articles": data.get("article_count") or 0,
        "likes": data.get("like_num") or 0,
        "official": official,
        "vip": vip,
        "url": f"https://space.bilibili.com/{mid}",
    }


async def get_user_live_room(mid: str, cookies: Optional[dict] = None) -> Optional[Dict]:
    """用户对应的直播间（没有直播间时返回 None）"""
    payload = await request_json(
        "https://api.live.bilibili.com/room/v1/Room/getRoomInfoOld",
        {"mid": mid},
        cookies=cookies,
    )
    data = payload.get("data") or {}
    room_id = data.get("roomid") or 0
    if not room_id:
        return None
    status = int(data.get("liveStatus") or 0)
    return {
        "room_id": room_id,
        "title": data.get("title") or "",
        "live_status": LIVE_STATUS.get(status, str(status)),
        "url": f"https://live.bilibili.com/{room_id}",
    }


# ==================== 直播间 ====================


async def _get_live_anchor(uid: int, cookies: Optional[dict] = None) -> Dict:
    payload = await request_json(
        "https://api.live.bilibili.com/live_user/v1/Master/info",
        {"uid": uid},
        cookies=cookies,
    )
    data = payload.get("data") or {}
    info = data.get("info") or {}
    level = ((data.get("exp") or {}).get("master_level") or {}).get("level")
    return {
        "uid": str(info.get("uid") or uid),
        "name": info.get("uname") or "",
        "official": (info.get("official_verify") or {}).get("desc") or "",
        "anchor_level": level or 0,
        "followers": data.get("follower_num") or 0,
        "medal_name": data.get("medal_name") or "",
        "room_news": (data.get("room_news") or {}).get("content") or "",
        "space_url": f"https://space.bilibili.com/{info.get('uid') or uid}",
    }


async def get_live_room(room_id: int, cookies: Optional[dict] = None) -> Dict:
    """直播间信息（支持短号）+ 主播信息"""
    payload = await request_json(
        "https://api.live.bilibili.com/room/v1/Room/get_info",
        {"room_id": int(room_id)},
        cookies=cookies,
    )
    data = payload.get("data") or {}
    if not data.get("room_id"):
        raise RuntimeError(f"未找到直播间 {room_id}")
    real_id = data["room_id"]
    status = int(data.get("live_status") or 0)
    uid = data.get("uid") or 0
    result = {
        "room_id": real_id,
        "short_id": data.get("short_id") or 0,
        "uid": str(uid),
        "title": data.get("title") or "",
        "live_status": LIVE_STATUS.get(status, str(status)),
        "live_time": data.get("live_time") if status == 1 else "",
        "area": " / ".join(
            name for name in (data.get("parent_area_name"), data.get("area_name")) if name
        ),
        "tags": data.get("tags") or "",
        "online": data.get("online") or 0,
        "followers": data.get("attention") or 0,
        "description": _clip(html_to_text(data.get("description") or ""), 500),
        "cover": data.get("user_cover") or "",
        "keyframe": data.get("keyframe") or "",
        "url": f"https://live.bilibili.com/{real_id}",
    }
    if uid:
        try:
            result["anchor"] = await _get_live_anchor(uid, cookies)
        except Exception as e:
            logger.warning(f"获取主播信息失败: {e}")
    return result


# ==================== 番剧 / 影视 ====================


async def get_bangumi_season(
    season_id: Optional[int] = None,
    ep_id: Optional[int] = None,
    media_id: Optional[int] = None,
    cookies: Optional[dict] = None,
) -> Dict:
    """获取剧集原始数据，season_id / ep_id / media_id 三选一"""
    if media_id and not season_id and not ep_id:
        payload = await request_json(
            "https://api.bilibili.com/pgc/review/user",
            {"media_id": int(media_id)},
            cookies=cookies,
        )
        season_id = ((payload.get("result") or {}).get("media") or {}).get("season_id")
        if not season_id:
            raise RuntimeError(f"未找到剧集 md{media_id}")
    if season_id:
        params = {"season_id": int(season_id)}
    elif ep_id:
        params = {"ep_id": int(ep_id)}
    else:
        raise ValueError("需要 season_id、ep_id 或 media_id")
    payload = await request_json(
        "https://api.bilibili.com/pgc/view/web/season", params, cookies=cookies
    )
    result = payload.get("result") or {}
    if not result:
        raise RuntimeError("未找到剧集")
    return result


def format_episode(ep: dict) -> Dict:
    ep_id = ep.get("ep_id") or ep.get("id") or 0
    title = ep.get("show_title") or " ".join(
        part for part in (ep.get("title"), ep.get("long_title")) if part
    )
    return {
        "ep_id": ep_id,
        "title": title,
        "bvid": ep.get("bvid") or "",
        "aid": ep.get("aid") or 0,
        "duration": int((ep.get("duration") or 0) / 1000),
        "pubdate": format_ts(ep.get("pub_time")),
        "badge": ep.get("badge") or (ep.get("badge_info") or {}).get("text") or "",
        "url": ep.get("link") or ep.get("share_url") or f"https://www.bilibili.com/bangumi/play/ep{ep_id}",
    }


def season_episodes(result: dict, include_sections: bool = True) -> List[dict]:
    """正片分集（可附带 PV/SP 等花絮分集）"""
    episodes = list(result.get("episodes") or [])
    if include_sections:
        for section in result.get("section") or []:
            episodes.extend(section.get("episodes") or [])
    return episodes


def find_episode(result: dict, ep_id: int) -> Optional[Dict]:
    for ep in season_episodes(result):
        if int(ep.get("ep_id") or ep.get("id") or 0) == int(ep_id):
            return format_episode(ep)
    return None


def format_bangumi_season(
    result: dict,
    episode_offset: int = 0,
    episode_limit: int = 30,
) -> Dict:
    episodes = result.get("episodes") or []
    episode_offset = max(0, int(episode_offset))
    episode_limit = min(100, max(1, int(episode_limit)))
    page = episodes[episode_offset:episode_offset + episode_limit]
    stat = result.get("stat") or {}
    rating = result.get("rating") or {}
    publish = result.get("publish") or {}
    extras = sum(len(s.get("episodes") or []) for s in result.get("section") or [])
    info = {
        "season_id": result.get("season_id") or 0,
        "media_id": result.get("media_id") or 0,
        "title": result.get("season_title") or result.get("title") or "",
        "series_title": result.get("title") or "",
        "type": SEASON_TYPES.get(result.get("type"), str(result.get("type") or "")),
        "description": _clip(result.get("evaluate") or "", 800),
        "areas": "、".join(a.get("name", "") for a in result.get("areas") or []),
        "styles": "、".join(result.get("styles") or []),
        "publish_time": publish.get("pub_time") or "",
        "is_finished": bool(publish.get("is_finish")),
        "progress": (result.get("new_ep") or {}).get("desc") or "",
        "rating": rating.get("score") or None,
        "rating_count": rating.get("count") or 0,
        "stats": {
            "views": stat.get("views") or 0,
            "danmaku": stat.get("danmakus") or 0,
            "followers": stat.get("favorites") or 0,
            "coins": stat.get("coins") or 0,
            "likes": stat.get("likes") or 0,
            "reply": stat.get("reply") or 0,
            "share": stat.get("share") or 0,
        },
        "actors": _clip(result.get("actors") or "", 300),
        "staff": _clip(result.get("staff") or "", 300),
        "payment_tip": (result.get("payment") or {}).get("tip") or "",
        "url": result.get("share_url") or result.get("link") or "",
        "total_episodes": len(episodes),
        "extra_episodes": extras,
        "episode_offset": episode_offset,
        "episodes": [format_episode(ep) for ep in page],
        "has_more_episodes": episode_offset + len(page) < len(episodes),
    }
    related = [
        {"season_id": s.get("season_id"), "title": s.get("season_title") or s.get("title") or ""}
        for s in result.get("seasons") or []
        if s.get("season_id") and s.get("season_id") != result.get("season_id")
    ]
    if related:
        info["related_seasons"] = related
    return info


# ==================== 专栏 / 图文动态 ====================


def _collect_words(node, out: List[str]) -> None:
    if isinstance(node, dict):
        word = node.get("word")
        if isinstance(word, dict) and isinstance(word.get("words"), str):
            out.append(word["words"])
            return
        rich = node.get("rich")
        if isinstance(rich, dict) and rich.get("text"):
            out.append(str(rich["text"]))
            return
        for value in node.values():
            _collect_words(value, out)
    elif isinstance(node, list):
        for value in node:
            _collect_words(value, out)


def opus_paragraphs_to_text(paragraphs: List[dict]) -> str:
    lines = []
    for para in paragraphs or []:
        pics = (para.get("pic") or {}).get("pics")
        if pics:
            lines.append("[图片]" if len(pics) == 1 else f"[图片×{len(pics)}]")
            continue
        code = para.get("code")
        if isinstance(code, dict) and code.get("content"):
            lines.append(str(code["content"]))
            continue
        items = (para.get("list") or {}).get("items")
        if items:
            for item in items:
                words: List[str] = []
                _collect_words(item, words)
                if "".join(words).strip():
                    lines.append("- " + "".join(words).strip())
            continue
        words = []
        _collect_words(para, words)
        text = "".join(words).strip()
        if text:
            lines.append(text)
    return "\n".join(lines)


def article_content_to_text(content: str) -> str:
    """专栏 content 可能是 HTML 或纯文本；JSON 富文本交给 opus 接口处理"""
    content = (content or "").strip()
    if not content or content[0] in "{[":
        return ""
    if re.search(r"<(p|br|figure|img|h[1-6]|div)\b", content, re.I):
        return html_to_text(content)
    return content


async def get_opus(opus_id: str, cookies: Optional[dict] = None) -> Dict:
    """图文动态 / 新版专栏（opus）详情与正文"""
    payload = await request_json(
        "https://api.bilibili.com/x/polymer/web-dynamic/v1/opus/detail",
        {"id": str(opus_id), "timezone_offset": -480, "features": "htmlNewStyle"},
        cookies=cookies,
        wbi=True,
    )
    item = (payload.get("data") or {}).get("item") or {}
    if not item:
        raise RuntimeError(f"未找到动态 {opus_id}")
    basic = item.get("basic") or {}
    modules = {m.get("module_type"): m for m in item.get("modules") or []}
    title = ((modules.get("MODULE_TYPE_TITLE") or {}).get("module_title") or {}).get("text") or ""
    author = (modules.get("MODULE_TYPE_AUTHOR") or {}).get("module_author") or {}
    content = (modules.get("MODULE_TYPE_CONTENT") or {}).get("module_content") or {}
    stat = (modules.get("MODULE_TYPE_STAT") or {}).get("module_stat") or {}
    comment_type = int(basic.get("comment_type") or 0)
    return {
        "opus_id": str(opus_id),
        "title": title,
        "author": author.get("name") or "",
        "mid": str(author.get("mid") or basic.get("uid") or ""),
        "publish_time": format_ts(author.get("pub_ts")) or author.get("pub_time") or "",
        "stats": {
            key: (stat.get(key) or {}).get("count") or 0
            for key in ("like", "comment", "forward")
        },
        "content": opus_paragraphs_to_text(content.get("paragraphs") or []),
        "comment_type": comment_type,
        "comment_oid": str(basic.get("comment_id_str") or ""),
        "article_id": str(basic.get("rid_str") or "") if comment_type == 12 else "",
        "url": f"https://www.bilibili.com/opus/{opus_id}",
    }


async def get_article(cvid: int, cookies: Optional[dict] = None) -> Dict:
    """专栏文章元信息与正文；未登录被风控时退回只取元信息"""
    url = f"https://www.bilibili.com/read/cv{cvid}"
    try:
        payload = await request_json(
            "https://api.bilibili.com/x/article/view",
            {"id": int(cvid), "gaia_source": "main_web", "web_location": "333.976"},
            cookies=cookies,
            wbi=True,
        )
    except Exception as e:
        logger.warning(f"获取专栏正文失败，改为只取元信息: {e}")
        payload = await request_json(
            "https://api.bilibili.com/x/article/viewinfo",
            {"id": int(cvid)},
            cookies=cookies,
        )
        data = payload.get("data") or {}
        stats = data.get("stats") or {}
        return {
            "article_id": int(cvid),
            "title": data.get("title") or "",
            "author": data.get("author_name") or "",
            "mid": str(data.get("mid") or ""),
            "stats": {k: stats.get(k) or 0 for k in ("view", "like", "reply", "favorite", "coin", "share")},
            "url": url,
            "content": "",
            "content_error": f"无法获取正文: {e}",
        }

    data = payload.get("data") or {}
    stats = data.get("stats") or {}
    author = data.get("author") or {}
    opus_id = str((data.get("opus") or {}).get("opus_id") or data.get("dyn_id_str") or "")
    content = article_content_to_text(data.get("content") or "")
    if not content and opus_id:
        try:
            content = (await get_opus(opus_id, cookies))["content"]
        except Exception as e:
            logger.warning(f"通过 opus 获取专栏正文失败: {e}")
    return {
        "article_id": int(cvid),
        "title": data.get("title") or "",
        "author": author.get("name") or "",
        "mid": str(author.get("mid") or ""),
        "category": (data.get("category") or {}).get("name") or "",
        "tags": [t.get("name") for t in data.get("tags") or [] if t.get("name")],
        "summary": _clip(data.get("summary") or "", 300),
        "publish_time": format_ts(data.get("publish_time")),
        "words": data.get("words") or 0,
        "stats": {k: stats.get(k) or 0 for k in ("view", "like", "reply", "favorite", "coin", "share")},
        "opus_id": opus_id,
        "url": url,
        "content": content,
    }


# ==================== 音频 ====================


async def get_audio(
    sid: int,
    include_lyrics: bool = True,
    cookies: Optional[dict] = None,
) -> Dict:
    """音频（au 号）信息与歌词"""
    payload = await request_json(
        "https://www.bilibili.com/audio/music-service-c/web/song/info",
        {"sid": int(sid)},
        cookies=cookies,
    )
    data = payload.get("data") or {}
    if not data or not data.get("id"):
        raise RuntimeError(f"未找到音频 au{sid}")
    stat = data.get("statistic") or {}
    bvid = data.get("bvid") or ""
    result = {
        "sid": data.get("id"),
        "title": data.get("title") or "",
        "author": data.get("author") or "",
        "uploader": data.get("uname") or "",
        "uid": str(data.get("uid") or ""),
        "intro": _clip(data.get("intro") or "", 1000),
        "duration": data.get("duration") or 0,
        "pubdate": format_ts(data.get("passtime")),
        "stats": {
            "play": stat.get("play") or 0,
            "collect": stat.get("collect") or 0,
            "comment": stat.get("comment") or 0,
            "share": stat.get("share") or 0,
            "coin": data.get("coin_num") or 0,
        },
        "bvid": bvid,
        "video_url": f"https://www.bilibili.com/video/{bvid}" if bvid else "",
        "url": f"https://www.bilibili.com/audio/au{data.get('id')}",
    }
    if include_lyrics:
        try:
            lyric = await request_json(
                "https://www.bilibili.com/audio/music-service-c/web/song/lyric",
                {"sid": int(sid)},
                cookies=cookies,
            )
            result["lyrics"] = str(lyric.get("data") or "").strip()
        except Exception as e:
            result["lyrics"] = ""
            result["lyrics_error"] = str(e)
    return result
