import mimetypes
import os
import uuid
from typing import Optional

import requests

from astrbot.api import logger

from ..models.transcriber_model import TranscriptResult, TranscriptSegment


class LocalMultimodalInfraTranscriber:
    """通过 local-multimodal-infra 的 legacy RPC 上传并转写音频。"""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:17890",
        token: str = "",
        model: str = "sensevoice-small-onnx",
        timeout: int = 600,
        timestamp_granularity_sec: int = 10,
        speaker_diarization: bool = True,
        session: Optional[requests.Session] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.token = token.strip()
        self.model = model.strip() or "sensevoice-small-onnx"
        self.timeout = max(30, int(timeout))
        self.timestamp_granularity_sec = min(
            120, max(1, int(timestamp_granularity_sec))
        )
        self.speaker_diarization = bool(speaker_diarization)
        self.session = session or requests.Session()

    @property
    def rpc_url(self) -> str:
        return f"{self.base_url}/rpc/infer"

    def _rpc(self, method: str, params: dict, timeout: int = 30) -> dict:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        response = self.session.post(
            self.rpc_url,
            json={
                "jsonrpc": "2.0",
                "id": f"bilivideo-{uuid.uuid4().hex}",
                "method": method,
                "params": params,
            },
            headers=headers,
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("error"):
            error = payload["error"]
            message = error.get("message", str(error)) if isinstance(error, dict) else str(error)
            raise RuntimeError(f"local-multimodal-infra RPC {method} 失败: {message}")
        result = payload.get("result")
        if not isinstance(result, dict):
            raise RuntimeError(
                f"local-multimodal-infra RPC {method} 返回格式无效"
            )
        return result

    @staticmethod
    def _find_audio_upload(task: dict) -> dict:
        for upload in task.get("uploads") or []:
            if upload.get("role") == "audio" or upload.get("slot") == "audio":
                return upload
        raise RuntimeError("local-multimodal-infra 未返回 audio 上传槽")

    def transcript(self, file_path: str) -> TranscriptResult:
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"音频文件不存在: {file_path}")

        mime = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
        file_name = os.path.basename(file_path)
        logger.info(
            f"使用 local-multimodal-infra 转写: model={self.model}, file={file_name}"
        )

        task = self._rpc(
            "create_task",
            {
                "task_kind": "asr.transcribe",
                "model": self.model,
                "files": [
                    {
                        "name": file_name,
                        "mime": mime,
                        "role": "audio",
                        "required": True,
                    }
                ],
                "params": {
                    "timestamps": True,
                    "timestamp_granularity_sec": self.timestamp_granularity_sec,
                    "speaker_diarization": self.speaker_diarization,
                    "token_timestamps": False,
                },
            },
        )
        upload = self._find_audio_upload(task)
        upload_url = upload.get("upload_url")
        if not upload_url:
            raise RuntimeError("local-multimodal-infra 未返回 upload_url")

        with open(file_path, "rb") as audio_file:
            response = self.session.post(
                upload_url,
                data=audio_file,
                headers={"Content-Type": mime},
                timeout=self.timeout,
            )
        response.raise_for_status()

        result = self._rpc(
            "start_task",
            {
                "task_id": task["task_id"],
                "wait": True,
                "timeout_sec": self.timeout,
            },
            timeout=self.timeout + 10,
        )
        if result.get("state") != "succeeded":
            raise RuntimeError(
                "local-multimodal-infra 转写未成功: "
                f"state={result.get('state')}, error={result.get('error')}"
            )

        output = result.get("output") or {}
        if output.get("type") not in (None, "asr_transcription"):
            raise RuntimeError(
                f"local-multimodal-infra 返回了非 ASR 结果: {output.get('type')}"
            )

        full_text = str(output.get("text") or "").strip()
        segments = []
        for item in output.get("segments") or []:
            text = str(item.get("text") or "").strip()
            if not text:
                continue
            segments.append(
                TranscriptSegment(
                    start=float(item.get("start_ms", 0)) / 1000.0,
                    end=float(item.get("end_ms", 0)) / 1000.0,
                    text=text,
                    speaker=item.get("speaker"),
                )
            )

        if not segments and full_text:
            segments.append(TranscriptSegment(start=0, end=0, text=full_text))
        if not full_text:
            full_text = " ".join(segment.text for segment in segments).strip()
        if not full_text:
            raise RuntimeError("local-multimodal-infra 返回了空转写")

        return TranscriptResult(
            language=None,
            full_text=full_text,
            segments=segments,
            raw={
                "source": "local_multimodal_infra",
                "task_id": result.get("task_id"),
                **output,
            },
        )
