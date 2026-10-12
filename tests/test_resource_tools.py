import json

import pytest

import astrbot_plugin_biliVideo.main as main_module
from astrbot_plugin_biliVideo.main import BiliVideoPlugin
from astrbot_plugin_biliVideo.services import bilibili_resources
from astrbot_plugin_biliVideo.services.bilibili_resources import (
    article_content_to_text,
    format_bangumi_season,
    html_to_text,
    opus_paragraphs_to_text,
    search_by_type,
)
from astrbot_plugin_biliVideo.utils.url_parser import parse_bilibili_target


def make_plugin():
    plugin = BiliVideoPlugin.__new__(BiliVideoPlugin)
    plugin.bili_cookies = {"SESSDATA": "x"}
    plugin._check_access = lambda _event: True
    plugin._debug_mode = False
    plugin.config = {}
    return plugin


SEASON = {
    "season_id": 1,
    "title": "测试番",
    "type": 1,
    "episodes": [
        {"ep_id": 11, "title": "1", "long_title": "开端", "bvid": "BV1aaaaaaaaa", "aid": 101, "duration": 60000},
        {"ep_id": 12, "title": "2", "long_title": "", "bvid": "BV1bbbbbbbbb", "aid": 102, "badge": "会员"},
    ],
    "section": [{"episodes": [{"ep_id": 90, "title": "PV", "bvid": "BV1ccccccccc", "aid": 190}]}],
    "seasons": [{"season_id": 1, "season_title": "测试番"}, {"season_id": 2, "season_title": "第二季"}],
}


@pytest.mark.parametrize(
    "text, expected",
    [
        ("BV1yW4y1j7Ft", ("video", "BV1yW4y1j7Ft")),
        ("https://www.bilibili.com/bangumi/play/ep693247?from=search", ("episode", "693247")),
        ("ss43164", ("season", "43164")),
        ("https://www.bilibili.com/bangumi/media/md28339735/", ("media", "28339735")),
        ("https://www.bilibili.com/read/cv26325382/", ("article", "26325382")),
        ("https://www.bilibili.com/opus/837809018364756009", ("opus", "837809018364756009")),
        ("https://t.bilibili.com/837809018364756009", ("opus", "837809018364756009")),
        ("AU13598", ("audio", "13598")),
        ("https://live.bilibili.com/21452505?spm_id_from=1", ("live", "21452505")),
        ("https://space.bilibili.com/2/video", ("user", "2")),
        ("av170001", ("video_aid", "170001")),
        ("java123", None),
    ],
)
def test_parse_bilibili_target(text, expected):
    assert parse_bilibili_target(text) == expected


@pytest.mark.asyncio
async def test_search_by_type_live_and_music(monkeypatch):
    calls = []

    async def fake_request(url, params=None, cookies=None, wbi=False):
        calls.append(params)
        if params["search_type"] == "live":
            return {
                "data": {
                    "pageinfo": {"live_room": {"numResults": 3}, "live_user": {"numResults": 2}},
                    "result": {
                        "live_room": [{"roomid": 7, "title": '<em class="keyword">歌</em>', "live_status": 1, "live_time": "t"}],
                        "live_user": [{"roomid": 8, "uname": "主播", "is_live": True}],
                    },
                }
            }
        return {"data": {"numResults": 1, "result": [{"bvid": "BV1aaaaaaaaa", "title": "曲", "pubdate": 0}, {"title": "无 bvid"}]}}

    monkeypatch.setattr(bilibili_resources, "request_json", fake_request)

    live = await search_by_type("歌", "live", order="live_time")
    assert calls[-1]["order"] == "live_time"
    assert [r["kind"] for r in live["results"]] == ["live_room", "live_user"]
    assert live["results"][0]["title"] == "歌" and live["results"][0]["live_status"] == "直播中"
    assert live["total"] == 5

    music = await search_by_type("曲", "music", order="bogus")
    assert calls[-1]["search_type"] == "video" and calls[-1]["tids"] == 3
    assert "order" not in calls[-1]
    assert [r["bvid"] for r in music["results"]] == ["BV1aaaaaaaaa"]

    with pytest.raises(ValueError):
        await search_by_type("x", "photo")


def test_text_extraction_helpers():
    html = '<p>第一段&amp;<br/>换行</p><figure><img src="//a.jpg"/></figure><h2>标题</h2><div>   多   空格  </div>'
    assert html_to_text(html) == "第一段&\n换行\n[图片]\n标题\n多 空格"
    assert article_content_to_text("纯文本\n第二行") == "纯文本\n第二行"
    assert article_content_to_text('{"ops": []}') == ""

    paragraphs = [
        {"para_type": 1, "text": {"nodes": [{"word": {"words": "你好"}}, {"rich": {"text": "@某人"}}]}},
        {"para_type": 2, "pic": {"pics": [{}, {}]}},
        {"para_type": 6, "list": {"items": [{"nodes": [{"word": {"words": "一"}}]}, {"nodes": [{"word": {"words": "二"}}]}]}},
        {"para_type": 7, "code": {"content": "print(1)"}},
    ]
    assert opus_paragraphs_to_text(paragraphs) == "你好@某人\n[图片×2]\n- 一\n- 二\nprint(1)"


def test_format_bangumi_season_paginates_episodes():
    info = format_bangumi_season(SEASON, episode_offset=1, episode_limit=1)
    assert info["total_episodes"] == 2 and info["extra_episodes"] == 1
    assert [e["ep_id"] for e in info["episodes"]] == [12]
    assert info["episodes"][0]["badge"] == "会员"
    assert info["has_more_episodes"] is False
    assert info["related_seasons"] == [{"season_id": 2, "title": "第二季"}]


@pytest.mark.asyncio
async def test_resolve_bvid_from_episode_and_season(monkeypatch):
    async def fake_season(season_id=None, ep_id=None, media_id=None, cookies=None):
        return SEASON

    monkeypatch.setattr(main_module, "get_bangumi_season", fake_season)
    plugin = make_plugin()
    assert await plugin._resolve_tool_bvid("https://www.bilibili.com/bangumi/play/ep12") == "BV1bbbbbbbbb"
    assert await plugin._resolve_tool_bvid("ep90") == "BV1ccccccccc"
    with pytest.raises(ValueError, match="共 2 集"):
        await plugin._resolve_tool_bvid("ss1")


@pytest.mark.asyncio
async def test_comments_tool_routes_comment_types(monkeypatch):
    calls = []

    async def fake_comments(oid, comment_type=1, limit=10, sort="hot", offset="", cookies=None):
        calls.append((oid, comment_type, limit, sort))
        return {"comments": []}

    async def fake_opus(opus_id, cookies=None):
        return {"comment_type": 11, "comment_oid": "555"}

    async def fake_season(season_id=None, ep_id=None, media_id=None, cookies=None):
        return SEASON

    async def fake_video_info(bvid, cookies=None):
        return {"aid": {"BV1aaaaaaaaa": 101}[bvid]}

    monkeypatch.setattr(main_module, "get_comments", fake_comments)
    monkeypatch.setattr(main_module, "get_opus", fake_opus)
    monkeypatch.setattr(main_module, "get_bangumi_season", fake_season)
    monkeypatch.setattr(main_module, "get_video_info", fake_video_info)
    plugin = make_plugin()

    for target in ("cv26325382", "au13598", "https://www.bilibili.com/opus/1", "ep11", "av7"):
        result = json.loads(await plugin.bilibili_get_comments(None, target, limit=3, sort="time"))
        assert result["success"] is True
    assert calls == [
        (26325382, 12, 3, "time"),
        (13598, 14, 3, "time"),
        (555, 11, 3, "time"),
        (101, 1, 3, "time"),
        (7, 1, 3, "time"),
    ]

    bad = json.loads(await plugin.bilibili_get_comments(None, "随便什么"))
    assert bad["success"] is False


@pytest.mark.asyncio
async def test_live_room_tool_accepts_room_link_and_uid(monkeypatch):
    rooms = []

    async def fake_live_room(room_id, cookies=None):
        rooms.append(room_id)
        return {"room_id": room_id}

    async def fake_user_room(mid, cookies=None):
        return {"room_id": 4321} if mid == "99" else None

    monkeypatch.setattr(main_module, "get_live_room", fake_live_room)
    monkeypatch.setattr(main_module, "get_user_live_room", fake_user_room)
    plugin = make_plugin()

    await plugin.bilibili_get_live_room(None, "https://live.bilibili.com/1234")
    await plugin.bilibili_get_live_room(None, "1024")
    await plugin.bilibili_get_live_room(None, "UID:99")
    await plugin.bilibili_get_live_room(None, "https://space.bilibili.com/99")
    assert rooms == [1234, 1024, 4321, 4321]

    missing = json.loads(await plugin.bilibili_get_live_room(None, "uid 5"))
    assert missing["success"] is False and "没有开通直播间" in missing["error"]
