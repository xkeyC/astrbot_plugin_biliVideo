import asyncio
import json
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

import astrbot_plugin_biliVideo.main as main_module
from astrbot.core.pipeline.process_stage.stage import ProcessStage
from astrbot_plugin_biliVideo.main import BiliVideoPlugin
from astrbot_plugin_biliVideo.models.audio_model import AudioDownloadResult
from astrbot_plugin_biliVideo.models.transcriber_model import (
    TranscriptResult,
    TranscriptSegment,
)
from astrbot_plugin_biliVideo.services.bilibili_api import _strip_search_highlight
from astrbot_plugin_biliVideo.services.note_service import NoteService
from astrbot_plugin_biliVideo.transcriber.local_multimodal_infra import (
    LocalMultimodalInfraTranscriber,
)


class FakeResponse:
    def __init__(self, payload=None):
        self.payload = payload or {}

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self):
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        request = kwargs.get("json") or {}
        method = request.get("method")
        if method == "create_task":
            return FakeResponse(
                {
                    "result": {
                        "task_id": "task-1",
                        "uploads": [
                            {
                                "slot": "audio",
                                "role": "audio",
                                "upload_url": "http://127.0.0.1:17890/files/upload/task-1/audio?signed=1",
                            }
                        ],
                    }
                }
            )
        if method == "start_task":
            return FakeResponse(
                {
                    "result": {
                        "task_id": "task-1",
                        "state": "succeeded",
                        "output": {
                            "type": "asr_transcription",
                            "text": "第一句 第二句",
                            "timestamped_text": "[00:00:00.000] 第一句 [00:00:01.500] 第二句",
                            "segments": [
                                {
                                    "start_ms": 0,
                                    "end_ms": 1500,
                                    "text": "第一句",
                                    "speaker": "speaker_0",
                                },
                                {
                                    "start_ms": 1500,
                                    "end_ms": 3000,
                                    "text": "第二句",
                                    "speaker": "speaker_1",
                                },
                            ],
                        },
                    }
                }
            )
        return FakeResponse({"ok": True})


class AutoDetectEvent:
    def __init__(self, wake: bool):
        self.message_str = "@bot 看看 BV1xx411c7mD 并告诉我你的看法"
        self.message_obj = None
        self.is_at_or_wake_command = wake
        self._extras = {}
        self.sent = []
        self._has_send_oper = False
        self.call_llm = False

    def chain_result(self, chain):
        return ("chain_result", chain)

    def get_extra(self, key, default=None):
        return self._extras.get(key, default)

    def set_extra(self, key, value):
        self._extras[key] = value

    def get_result(self):
        return None

    async def send(self, chain):
        self.sent.append(chain)
        self._has_send_oper = True


def make_auto_detect_plugin(auto_summary: bool = False):
    plugin = BiliVideoPlugin.__new__(BiliVideoPlugin)
    plugin.enable_miniapp_detect = True
    plugin.bili_cookies = {}
    plugin.config = {
        "detect_show_cover": False,
        "detect_auto_summary": auto_summary,
        "summary_progress_template": "正在总结",
    }
    plugin._side_tasks = set()
    plugin._check_detect_access = lambda _event: True
    plugin._log = lambda _message: None
    plugin._log_always = lambda _message: None
    plugin._format_video_info = lambda _info, bvid: f"视频状态 {bvid}"

    async def no_history(_event, _bvid):
        return {"summary": None, "video_info": None}

    plugin._find_bvid_history = no_history
    return plugin


def test_local_multimodal_infra_uses_upload_task_flow(tmp_path: Path):
    audio = tmp_path / "sample.mp3"
    audio.write_bytes(b"fake audio")
    session = FakeSession()
    transcriber = LocalMultimodalInfraTranscriber(
        token="infer-secret",
        timeout=45,
        timestamp_granularity_sec=8,
        session=session,
    )

    result = transcriber.transcript(str(audio))

    assert result.full_text == "第一句 第二句"
    assert [segment.speaker for segment in result.segments] == [
        "speaker_0",
        "speaker_1",
    ]
    assert result.raw["source"] == "local_multimodal_infra"
    create_call = session.calls[0][1]
    assert create_call["headers"]["Authorization"] == "Bearer infer-secret"
    params = create_call["json"]["params"]
    assert params["task_kind"] == "asr.transcribe"
    assert params["params"] == {
        "timestamps": True,
        "timestamp_granularity_sec": 8,
        "speaker_diarization": True,
        "token_timestamps": False,
    }
    assert session.calls[1][0].startswith(
        "http://127.0.0.1:17890/files/upload/task-1/audio"
    )
    assert session.calls[2][1]["json"]["method"] == "start_task"


def test_note_service_selects_local_provider(tmp_path: Path):
    service = NoteService(
        str(tmp_path),
        asr_provider="local_multimodal_infra",
        local_infra_model="sensevoice-small-onnx",
    )
    assert isinstance(service.transcriber, LocalMultimodalInfraTranscriber)


@pytest.mark.asyncio
async def test_extract_content_prefers_subtitle_without_audio_download():
    subtitle = TranscriptResult(
        language="zh-Hans",
        full_text="字幕内容",
        segments=[TranscriptSegment(start=0, end=1, text="字幕内容")],
        raw={"source": "bilibili_subtitle"},
    )

    class Downloader:
        def download_subtitles(self, _url):
            return subtitle

        def download(self, _url, quality="fast", audio_format="mp3"):
            raise AssertionError("已有字幕时不应下载音频")

    service = NoteService.__new__(NoteService)
    service.downloader = Downloader()
    result = await service.extract_content("https://example/video", source="auto")
    assert result is subtitle


@pytest.mark.asyncio
async def test_extract_content_falls_back_to_configured_asr(tmp_path: Path):
    audio = tmp_path / "audio.mp3"
    audio.write_bytes(b"audio")

    class Downloader:
        def download_subtitles(self, _url):
            return None

        def download(self, _url, quality="fast", audio_format="mp3"):
            assert audio_format == "wav"
            return AudioDownloadResult(
                file_path=str(audio),
                title="title",
                duration=1,
                cover_url=None,
                platform="bilibili",
                video_id="BV1xx411c7mD",
                raw_info={},
            )

    transcript = TranscriptResult(
        language=None,
        full_text="ASR 内容",
        segments=[TranscriptSegment(start=0, end=1, text="ASR 内容")],
        raw={"source": "local_multimodal_infra"},
    )

    class Transcriber:
        def transcript(self, file_path):
            assert file_path == str(audio)
            return transcript

    service = NoteService.__new__(NoteService)
    service.downloader = Downloader()
    service.transcriber = Transcriber()
    service.asr_provider = "local_multimodal_infra"
    service._cleanup = lambda file_path: Path(file_path).unlink(missing_ok=True)

    result = await service.extract_content("https://example/video", source="auto")
    assert result is transcript
    assert not audio.exists()


@pytest.mark.asyncio
async def test_shared_transcriber_is_serialized():
    state_lock = threading.Lock()
    state = {"active": 0, "max_active": 0}
    result = TranscriptResult(
        language=None,
        full_text="ok",
        segments=[TranscriptSegment(start=0, end=1, text="ok")],
    )

    class Transcriber:
        def transcript(self, _file_path):
            with state_lock:
                state["active"] += 1
                state["max_active"] = max(state["max_active"], state["active"])
            time.sleep(0.05)
            with state_lock:
                state["active"] -= 1
            return result

    service = NoteService.__new__(NoteService)
    service.transcriber = Transcriber()
    service._asr_lock = asyncio.Lock()
    outputs = await asyncio.gather(
        service._transcribe_audio("one.wav"),
        service._transcribe_audio("two.wav"),
    )
    assert outputs == [result, result]
    assert state["max_active"] == 1


def test_agent_content_payload_keeps_timestamps_and_speaker():
    transcript = TranscriptResult(
        language="zh",
        full_text="内容",
        segments=[
            TranscriptSegment(
                start=65,
                end=70,
                text="内容",
                speaker="speaker_0",
            )
        ],
        raw={"source": "local_multimodal_infra"},
    )
    payload = BiliVideoPlugin._transcript_tool_payload(transcript, 20000)
    assert payload["content"] == "[01:05] [speaker_0] 内容"
    assert payload["source"] == "local_multimodal_infra"
    assert payload["truncated"] is False


def test_search_highlight_is_removed():
    assert _strip_search_highlight('<em class="keyword">测试</em>视频') == "测试视频"


def test_asr_configuration_schema_is_valid():
    schema_path = Path(__file__).parents[1] / "_conf_schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    assert schema["asr_provider"]["options"] == [
        "bcut",
        "local_multimodal_infra",
    ]


@pytest.mark.asyncio
async def test_wake_message_queues_video_status_without_consuming_llm(
    monkeypatch,
):
    async def video_info(_bvid, cookies=None):
        return {"title": "测试视频", "pic": ""}

    monkeypatch.setattr(main_module, "get_video_info", video_info)
    plugin = make_auto_detect_plugin()
    queued = []
    plugin._queue_llm_side_message = lambda _event, chain: queued.append(chain)
    event = AutoDetectEvent(wake=True)

    yielded = [item async for item in plugin.on_all_message(event)]

    assert yielded == []
    assert len(queued) == 1
    assert queued[0][0].text == "视频状态 BV1xx411c7mD"


@pytest.mark.asyncio
async def test_plain_bv_message_keeps_normal_auto_detect_response(monkeypatch):
    async def video_info(_bvid, cookies=None):
        return {"title": "测试视频", "pic": ""}

    monkeypatch.setattr(main_module, "get_video_info", video_info)
    plugin = make_auto_detect_plugin()
    event = AutoDetectEvent(wake=False)

    yielded = [item async for item in plugin.on_all_message(event)]

    assert len(yielded) == 1
    assert yielded[0][0] == "chain_result"


@pytest.mark.asyncio
async def test_wake_auto_summary_runs_as_side_task(monkeypatch):
    async def video_info(_bvid, cookies=None):
        return {"title": "测试视频", "pic": ""}

    monkeypatch.setattr(main_module, "get_video_info", video_info)
    plugin = make_auto_detect_plugin(auto_summary=True)
    queued = []
    tracked = []
    plugin._queue_llm_side_message = lambda _event, chain: queued.append(chain)

    def track(coroutine, name):
        coroutine.close()
        tracked.append(name)

    plugin._track_side_task = track
    event = AutoDetectEvent(wake=True)

    yielded = [item async for item in plugin.on_all_message(event)]

    assert yielded == []
    assert len(queued) == 2
    assert tracked == ["bilivideo-auto-summary-BV1xx411c7mD"]


@pytest.mark.asyncio
async def test_llm_hook_flushes_side_message_once():
    plugin = make_auto_detect_plugin()
    event = AutoDetectEvent(wake=True)
    plugin._queue_llm_side_message(event, [main_module.Plain("视频状态")])

    assert event._has_send_oper is False
    await plugin.flush_bilibili_status_before_llm(event, None)
    await asyncio.sleep(0.06)

    assert len(event.sent) == 1
    assert event._has_send_oper is True
    assert event.sent[0].chain[0].text == "视频状态"


@pytest.mark.asyncio
async def test_process_stage_calls_llm_while_side_status_is_sent():
    plugin = make_auto_detect_plugin()
    event = AutoDetectEvent(wake=True)
    event.set_extra("activated_handlers", [object()])
    plugin._queue_llm_side_message(event, [main_module.Plain("视频状态")])

    class EmptyStarStage:
        async def process(self, _event):
            if False:
                yield

    class RecordingAgentStage:
        def __init__(self):
            self.called = False

        async def process(self, _event):
            self.called = True
            await asyncio.sleep(0.06)
            yield

    agent_stage = RecordingAgentStage()
    stage = ProcessStage.__new__(ProcessStage)
    stage.ctx = SimpleNamespace(
        astrbot_config={"provider_settings": {"enable": True}}
    )
    stage.star_request_sub_stage = EmptyStarStage()
    stage.agent_sub_stage = agent_stage

    async for _ in stage.process(event):
        pass

    assert agent_stage.called is True
    assert len(event.sent) == 1
    assert event.sent[0].chain[0].text == "视频状态"
