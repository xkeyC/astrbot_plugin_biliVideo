import json
import re
import uuid
from typing import Optional, List, Dict

import aiohttp

from astrbot.api import logger
from ..utils.wbi_sign import sign_wbi_params

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=10)

BILIBILI_API_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://www.bilibili.com',
}


def _strip_search_highlight(text: str) -> str:
    return re.sub(r"</?em(?:\s+class=\"keyword\")?>", "", text or "")


def _build_headers(cookies: Optional[dict] = None) -> dict:
    """构建带 Cookie 的请求头"""
    headers = dict(BILIBILI_API_HEADERS)
    cookie_dict = dict(cookies) if cookies else {}
    # B站搜索等 API 需要 buvid3 cookie
    if 'buvid3' not in cookie_dict:
        cookie_dict['buvid3'] = str(uuid.uuid4()) + "infoc"
    cookie_parts = [f'{k}={v}' for k, v in cookie_dict.items() if v]
    if cookie_parts:
        headers['Cookie'] = '; '.join(cookie_parts)
    return headers


async def get_up_info(mid: str, cookies: Optional[dict] = None) -> Optional[Dict]:
    """
    获取 UP主 基本信息

    :param mid: UP主 UID
    :param cookies: B站 cookie dict
    :return: {"mid", "name", "face", "sign"} 或 None
    """
    params = {"mid": mid}
    signed_params = await sign_wbi_params(params, cookies=cookies)

    url = "https://api.bilibili.com/x/space/wbi/acc/info"
    headers = _build_headers(cookies)

    try:
        async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
            async with session.get(url, params=signed_params, headers=headers) as resp:
                if resp.status != 200:
                    logger.warning(f"获取UP主信息失败, HTTP {resp.status}")
                    return None

                data = await resp.json()
                if data.get("code") != 0:
                    logger.warning(f"获取UP主信息失败: code={data.get('code')}, msg={data.get('message')}")
                    return None

                info = data.get("data") or {}
                return {
                    "mid": str(info.get("mid", mid)),
                    "name": info.get("name", "未知"),
                    "face": info.get("face", ""),
                    "sign": info.get("sign", ""),
                }
    except Exception as e:
        logger.error(f"获取UP主信息异常: {e}")
        return None


async def get_latest_videos(mid: str, count: int = 5, cookies: Optional[dict] = None) -> List[Dict]:
    """
    获取 UP主 最新投稿视频列表

    :param mid: UP主 UID
    :param count: 获取数量
    :param cookies: B站 cookie dict
    :return: 视频列表 [{"bvid", "title", "duration", "pubdate", "pic"}]
    """
    params = {
        "mid": mid,
        "ps": count,
        "pn": 1,
        "order": "pubdate",
    }
    signed_params = await sign_wbi_params(params, cookies=cookies)

    url = "https://api.bilibili.com/x/space/wbi/arc/search"
    headers = _build_headers(cookies)

    try:
        async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
            async with session.get(url, params=signed_params, headers=headers) as resp:
                if resp.status != 200:
                    logger.warning(f"获取UP主视频列表失败, HTTP {resp.status}")
                    return []

                data = await resp.json()
                if data.get("code") != 0:
                    logger.warning(f"获取UP主视频列表失败: code={data.get('code')}, msg={data.get('message')}")
                    return []

                vlist = (data.get("data") or {}).get("list") or {}
                vlist = vlist.get("vlist") or []
                result = []
                for v in vlist[:count]:
                    result.append({
                        "bvid": v.get("bvid", ""),
                        "title": v.get("title", ""),
                        "duration": v.get("length", ""),
                        "pubdate": v.get("created", 0),
                        "pic": v.get("pic", ""),
                        "description": v.get("description", ""),
                    })
                return result
    except Exception as e:
        logger.error(f"获取UP主视频列表异常: {e}")
        return []

async def search_up_by_name(keyword: str, cookies: Optional[dict] = None) -> Optional[Dict]:
    """
    通过关键词搜索UP主（返回粉丝最多的第一个）

    :param keyword: 搜索关键词（UP主昵称）
    :param cookies: B站 cookie dict
    :return: {"mid", "name"} 或 None
    """
    # 先尝试 WBI 签名版搜索接口
    params = {
        "search_type": "bili_user",
        "keyword": keyword,
        "page": 1,
        "order": "fans",
        "order_sort": 0,
    }
    signed_params = await sign_wbi_params(params, cookies=cookies)

    url = "https://api.bilibili.com/x/web-interface/wbi/search/type"
    headers = _build_headers(cookies)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=signed_params, headers=headers) as resp:
                if resp.status != 200:
                    logger.warning(f"搜索UP主失败, HTTP {resp.status}")
                    return None

                data = await resp.json()
                code = data.get("code")
                logger.info(f"搜索UP主 '{keyword}' 响应: code={code}, message={data.get('message')}")

                if code != 0:
                    logger.warning(f"搜索UP主失败: code={code}, msg={data.get('message')}")
                    # 回退到旧版搜索接口
                    return await _search_up_fallback(keyword, cookies)

                results = data.get("data", {}).get("result", [])
                if not results:
                    logger.info(f"搜索UP主 '{keyword}' 无结果")
                    return None

                # 优先精确匹配
                for r in results:
                    uname = r.get("uname", "")
                    # B站搜索结果的 uname 可能包含 <em> 高亮标签
                    clean_name = uname.replace("<em class=\"keyword\">", "").replace("</em>", "")
                    if clean_name == keyword:
                        return {
                            "mid": str(r.get("mid", "")),
                            "name": clean_name,
                        }

                # 无精确匹配，返回第一个
                first = results[0]
                uname = first.get("uname", "未知")
                clean_name = uname.replace("<em class=\"keyword\">", "").replace("</em>", "")
                return {
                    "mid": str(first.get("mid", "")),
                    "name": clean_name,
                }
    except Exception as e:
        logger.error(f"搜索UP主异常: {e}", exc_info=True)
        return await _search_up_fallback(keyword, cookies)


async def _search_up_fallback(keyword: str, cookies: Optional[dict] = None) -> Optional[Dict]:
    """旧版搜索接口（不需要 WBI 签名）"""
    url = "https://api.bilibili.com/x/web-interface/search/type"
    params = {
        "search_type": "bili_user",
        "keyword": keyword,
        "page": 1,
        "order": "fans",
    }
    headers = _build_headers(cookies)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as resp:
                if resp.status != 200:
                    logger.warning(f"搜索UP主(fallback)失败, HTTP {resp.status}")
                    return None

                data = await resp.json()
                code = data.get("code")
                logger.info(f"搜索UP主(fallback) '{keyword}' 响应: code={code}")

                if code != 0:
                    logger.warning(f"搜索UP主(fallback)失败: {data.get('message')}")
                    return None

                results = data.get("data", {}).get("result", [])
                if not results:
                    return None

                first = results[0]
                uname = first.get("uname", "未知")
                clean_name = uname.replace("<em class=\"keyword\">", "").replace("</em>", "")
                return {
                    "mid": str(first.get("mid", "")),
                    "name": clean_name,
                }
    except Exception as e:
        logger.error(f"搜索UP主(fallback)异常: {e}")
        return None


async def search_videos(
    keyword: str,
    page: int = 1,
    count: int = 10,
    order: str = "totalrank",
    cookies: Optional[dict] = None,
) -> List[Dict]:
    """按关键词搜索 B站视频。"""
    allowed_orders = {"totalrank", "click", "pubdate", "dm", "stow"}
    if order not in allowed_orders:
        order = "totalrank"
    page = max(1, int(page))
    count = min(20, max(1, int(count)))
    params = {
        "search_type": "video",
        "keyword": keyword.strip(),
        "page": page,
        "order": order,
        "duration": 0,
        "tids": 0,
    }
    signed_params = await sign_wbi_params(params, cookies=cookies)
    url = "https://api.bilibili.com/x/web-interface/wbi/search/type"

    try:
        async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
            async with session.get(
                url,
                params=signed_params,
                headers=_build_headers(cookies),
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"HTTP {resp.status}")
                payload = await resp.json()
                if payload.get("code") != 0:
                    raise RuntimeError(
                        f"code={payload.get('code')}, msg={payload.get('message')}"
                    )

        results = (payload.get("data") or {}).get("result") or []
        videos = []
        for item in results[:count]:
            bvid = item.get("bvid") or ""
            if not bvid:
                continue
            videos.append(
                {
                    "bvid": bvid,
                    "title": _strip_search_highlight(item.get("title") or ""),
                    "description": _strip_search_highlight(
                        item.get("description") or ""
                    ),
                    "author": item.get("author") or "",
                    "mid": str(item.get("mid") or ""),
                    "duration": item.get("duration") or "",
                    "play": item.get("play") or 0,
                    "danmaku": item.get("video_review") or 0,
                    "favorites": item.get("favorites") or 0,
                    "pubdate": item.get("pubdate") or 0,
                    "pic": item.get("pic") or "",
                    "url": f"https://www.bilibili.com/video/{bvid}",
                }
            )
        return videos
    except Exception as e:
        logger.error(f"搜索B站视频异常: {e}")
        raise RuntimeError(f"搜索B站视频失败: {e}") from e


async def get_video_info(bvid: str, cookies: Optional[dict] = None) -> Optional[Dict]:
    """
    获取视频详情信息

    :param bvid: 视频 BV 号
    :param cookies: B站 cookie dict
    :return: {"bvid", "title", "pic", "owner_name", "owner_mid", "view", "danmaku", "like", "desc"} 或 None
    """
    url = "https://api.bilibili.com/x/web-interface/view"
    params = {"bvid": bvid}
    headers = _build_headers(cookies)

    try:
        async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
            async with session.get(url, params=params, headers=headers) as resp:
                if resp.status != 200:
                    logger.warning(f"获取视频信息失败, HTTP {resp.status}")
                    return None

                data = await resp.json()
                if data.get("code") != 0:
                    logger.warning(f"获取视频信息失败: code={data.get('code')}, msg={data.get('message')}")
                    return None

                d = data.get("data") or {}
                owner = d.get("owner") or {}
                stat = d.get("stat") or {}
                return {
                    "bvid": d.get("bvid", bvid),
                    "aid": d.get("aid", 0),
                    "title": d.get("title", ""),
                    "pic": d.get("pic", ""),
                    "desc": d.get("desc", ""),
                    "pubdate": d.get("pubdate", 0),
                    "owner_name": owner.get("name", "未知"),
                    "owner_mid": str(owner.get("mid", "")),
                    "view": stat.get("view", 0),
                    "danmaku": stat.get("danmaku", 0),
                    "like": stat.get("like", 0),
                    "coin": stat.get("coin", 0),
                    "favorite": stat.get("favorite", 0),
                    "share": stat.get("share", 0),
                    "reply": stat.get("reply", 0),
                    "duration": d.get("duration", 0),
                    "pages": d.get("pages") or [],
                }
    except Exception as e:
        logger.error(f"获取视频信息异常: {e}")
        return None


def _format_comment(reply: dict, max_sub_replies: int = 0) -> Dict:
    member = reply.get("member") or {}
    content = reply.get("content") or {}
    item = {
        "rpid": str(reply.get("rpid") or ""),
        "user": member.get("uname", ""),
        "mid": str(reply.get("mid") or member.get("mid") or ""),
        "message": content.get("message", ""),
        "like": reply.get("like", 0),
        "reply_count": reply.get("rcount", 0),
        "ctime": reply.get("ctime", 0),
    }
    location = (reply.get("reply_control") or {}).get("location")
    if location:
        item["location"] = location
    if max_sub_replies > 0:
        sub_replies = [
            _format_comment(sub)
            for sub in (reply.get("replies") or [])[:max_sub_replies]
        ]
        if sub_replies:
            item["replies"] = sub_replies
    return item


async def get_video_comments(
    aid: int,
    limit: int = 10,
    sort: str = "hot",
    offset: str = "",
    cookies: Optional[dict] = None,
) -> Dict:
    """
    获取视频评论区（主楼 + 少量楼中楼）

    :param aid: 视频 av 号（oid）
    :param limit: 返回的主楼评论数量，1-20
    :param sort: hot(按热度) / time(按时间)
    :param offset: 翻页游标，取上一次返回的 next_offset
    :return: {"sort", "total", "comments", "next_offset", "is_end"}
    """
    limit = min(20, max(1, int(limit)))
    mode = 2 if sort == "time" else 3
    params = {
        "oid": int(aid),
        "type": 1,
        "mode": mode,
        "pagination_str": json.dumps({"offset": offset or ""}, separators=(",", ":")),
        "plat": 1,
        "web_location": 1315875,
    }
    if not offset:
        params["seek_rpid"] = ""
    signed_params = await sign_wbi_params(params, cookies=cookies)
    url = "https://api.bilibili.com/x/v2/reply/wbi/main"

    try:
        async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
            async with session.get(
                url,
                params=signed_params,
                headers=_build_headers(cookies),
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"HTTP {resp.status}")
                payload = await resp.json(content_type=None)
                if payload.get("code") != 0:
                    raise RuntimeError(
                        f"code={payload.get('code')}, msg={payload.get('message')}"
                    )
    except Exception as e:
        logger.error(f"获取视频评论异常: {e}")
        raise RuntimeError(f"获取视频评论失败: {e}") from e

    data = payload.get("data") or {}
    cursor = data.get("cursor") or {}
    comments = []
    seen = set()
    # 置顶评论只在第一页返回
    if not offset:
        top = (data.get("upper") or {}).get("top")
        for reply in [top, *(data.get("top_replies") or [])]:
            if reply and reply.get("rpid") not in seen:
                seen.add(reply.get("rpid"))
                comments.append({**_format_comment(reply, 3), "pinned": True})
    for reply in data.get("replies") or []:
        if len(comments) >= limit:
            break
        if reply.get("rpid") in seen:
            continue
        seen.add(reply.get("rpid"))
        comments.append(_format_comment(reply, 3))

    next_offset = (
        (cursor.get("pagination_reply") or {}).get("next_offset") or ""
    )
    return {
        "sort": "time" if mode == 2 else "hot",
        "total": cursor.get("all_count", 0),
        "comments": comments[:limit],
        "next_offset": next_offset,
        "is_end": bool(cursor.get("is_end")),
    }


async def resolve_short_url(short_url: str) -> Optional[str]:
    """
    异步解析短链接（如 b23.tv），返回跳转后的最终 URL
    """
    try:
        async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
            async with session.get(short_url, allow_redirects=True, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }) as resp:
                return str(resp.url)
    except Exception as e:
        logger.warning(f"解析短链接失败: {e}")
        return None
