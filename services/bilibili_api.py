import asyncio
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


class BiliApiError(RuntimeError):
    """B站接口返回非 0 code"""

    def __init__(self, code, message: str = ""):
        self.code = code
        hint = _ERROR_HINTS.get(str(code), "")
        super().__init__(f"code={code}, msg={message}{hint}")


_ERROR_HINTS = {
    "-101": "（需要登录，管理员可发送 /B站登录 扫码）",
    "-352": "（触发 B站风控，登录后通常可恢复，管理员可发送 /B站登录 扫码）",
    "-412": "（请求被 B站拦截，请稍后重试）",
    "-404": "（内容不存在或已删除）",
}


async def request_json(
    url: str,
    params: Optional[dict] = None,
    cookies: Optional[dict] = None,
    wbi: bool = False,
) -> dict:
    """GET B站接口并校验 code，返回完整响应体。"""
    params = dict(params or {})
    if wbi:
        params = await sign_wbi_params(params, cookies=cookies)
    try:
        async with aiohttp.ClientSession(timeout=REQUEST_TIMEOUT) as session:
            async with session.get(url, params=params, headers=_build_headers(cookies)) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"HTTP {resp.status}")
                payload = await resp.json(content_type=None)
    except asyncio.TimeoutError as e:
        raise RuntimeError(f"请求 B站接口超时: {url}") from e
    except aiohttp.ClientError as e:
        raise RuntimeError(f"请求 B站接口失败: {e or type(e).__name__}") from e
    code = payload.get("code")
    if code not in (0, "0"):
        raise BiliApiError(code, payload.get("message") or payload.get("msg") or "")
    return payload


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
    """获取视频评论区，oid 为视频 av 号。"""
    return await get_comments(
        aid, 1, limit=limit, sort=sort, offset=offset, cookies=cookies
    )


async def get_comments(
    oid: int,
    comment_type: int = 1,
    limit: int = 10,
    sort: str = "hot",
    offset: str = "",
    cookies: Optional[dict] = None,
) -> Dict:
    """
    获取评论区（主楼 + 少量楼中楼）

    :param oid: 评论区 id（视频/番剧分集为 av 号，专栏为 cv 号，音频为 au 号，动态为动态 id）
    :param comment_type: 评论区类型代码：1 视频、12 专栏、14 音频、11 图片动态、17 文字动态
    :param limit: 每页主楼评论数量，1-20（首页的置顶评论额外附加）
    :param sort: hot(按热度) / time(按时间)
    :param offset: 翻页游标，取上一次返回的 next_offset
    :return: {"sort", "total", "comments", "next_offset", "is_end"}
    """
    limit = min(20, max(1, int(limit)))
    mode = 2 if sort == "time" else 3
    params = {
        "oid": int(oid),
        "type": int(comment_type),
        "mode": mode,
        # 每页条数与 limit 一致，否则截断后游标会跳过本页剩余评论
        "ps": limit,
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
        logger.error(f"获取评论异常: {e}")
        raise RuntimeError(f"获取评论失败: {e}") from e

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
        "comments": comments,
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
