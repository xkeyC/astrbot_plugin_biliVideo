import asyncio
import os
import re
from typing import Optional, List

from astrbot.api import logger

from ..downloaders.bilibili_downloader import BilibiliDownloader
from ..transcriber.bcut import BcutTranscriber
from ..transcriber.local_multimodal_infra import LocalMultimodalInfraTranscriber
from ..models.transcriber_model import TranscriptResult
from ..gpt.prompt_builder import build_prompt
from ..utils.note_helper import replace_content_markers
from ..utils.url_parser import extract_video_id


class NoteService:
    """
    总结生成服务

    流程: 下载音频 → 获取字幕/转写 → LLM 总结 → 后处理 → 返回 Markdown
    """

    def __init__(
        self,
        data_dir: str,
        cookies: Optional[dict] = None,
        asr_provider: str = "bcut",
        local_infra_base_url: str = "http://127.0.0.1:17890",
        local_infra_token: str = "",
        local_infra_model: str = "sensevoice-small-onnx",
        asr_timeout: int = 600,
        timestamp_granularity_sec: int = 10,
        speaker_diarization: bool = True,
    ):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self._asr_lock = asyncio.Lock()
        self.downloader = BilibiliDownloader(
            data_dir=os.path.join(data_dir, "audio"),
            cookies=cookies,
        )
        self.asr_provider = asr_provider.strip().lower().replace("-", "_")
        if self.asr_provider == "local_multimodal_infra":
            self.transcriber = LocalMultimodalInfraTranscriber(
                base_url=local_infra_base_url,
                token=local_infra_token,
                model=local_infra_model,
                timeout=asr_timeout,
                timestamp_granularity_sec=timestamp_granularity_sec,
                speaker_diarization=speaker_diarization,
            )
        elif self.asr_provider == "bcut":
            self.transcriber = BcutTranscriber(timeout=asr_timeout)
        else:
            raise ValueError(
                "asr_provider 仅支持 bcut 或 local_multimodal_infra"
            )

    async def _transcribe_audio(self, file_path: str) -> TranscriptResult:
        """串行化共享转写器，避免必剪任务状态在并发请求间串线。"""
        if not hasattr(self, "_asr_lock"):
            self._asr_lock = asyncio.Lock()
        async with self._asr_lock:
            return await asyncio.get_running_loop().run_in_executor(
                None, lambda: self.transcriber.transcript(file_path)
            )

    async def extract_content(
        self,
        video_url: str,
        source: str = "auto",
        quality: str = "fast",
    ) -> TranscriptResult:
        """提取平台字幕或使用配置的 ASR 提供商转写。"""
        source = source.strip().lower()
        if source not in {"auto", "subtitle", "asr"}:
            raise ValueError("source 仅支持 auto、subtitle 或 asr")

        if source in {"auto", "subtitle"}:
            transcript = await asyncio.get_running_loop().run_in_executor(
                None, lambda: self.downloader.download_subtitles(video_url)
            )
            if transcript and transcript.segments:
                return transcript
            if source == "subtitle":
                raise RuntimeError("该视频没有可用的平台字幕")

        audio_meta = None
        try:
            audio_format = (
                "wav" if self.asr_provider == "local_multimodal_infra" else "mp3"
            )
            audio_meta = await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: self.downloader.download(
                    video_url, quality=quality, audio_format=audio_format
                ),
            )
            transcript = await self._transcribe_audio(audio_meta.file_path)
            if not transcript or not transcript.segments:
                raise RuntimeError("ASR 返回了空内容")
            return transcript
        finally:
            if audio_meta and audio_meta.file_path:
                self._cleanup(audio_meta.file_path)

    async def generate_note(
        self,
        video_url: str,
        llm_ask_func,
        style: str = "detailed",
        enable_link: bool = True,
        enable_summary: bool = True,
        quality: str = "fast",
        max_length: int = 3000,
        enable_split: bool = True,
        split_max_length: int = 2500,
        split_by_heading: bool = True,
    ) -> List[str]:
        """
        为单个视频生成总结

        :param video_url: B站视频链接
        :param llm_ask_func: 调用 AstrBot LLM 的异步函数, 签名: async (prompt: str) -> str
        :param style: 总结风格
        :param enable_link: 是否插入原片跳转
        :param enable_summary: 是否加 AI 总结
        :param quality: 音频下载质量
        :param max_length: 总结最大字符数（单段限制，用于提示LLM）
        :param enable_split: 启用分段发送
        :param split_max_length: 每段最大字符数
        :param split_by_heading: 按标题分段
        :return: Markdown 总结文本列表（分段）
        """
        audio_meta = None
        try:
            # 1. 优先尝试获取平台字幕（无需下载音频）
            logger.info("尝试获取平台字幕...")
            transcript = await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: self.downloader.download_subtitles(video_url)
            )

            # 2. 如果没有平台字幕，才下载音频并使用配置的 ASR 提供商转写
            if not transcript or not transcript.segments:
                logger.info("无平台字幕，开始下载音频并转写...")
                audio_format = (
                    "wav"
                    if self.asr_provider == "local_multimodal_infra"
                    else "mp3"
                )
                audio_meta = await asyncio.get_running_loop().run_in_executor(
                    None,
                    lambda: self.downloader.download(
                        video_url,
                        quality=quality,
                        audio_format=audio_format,
                    )
                )
                logger.info(f"音频下载完成: {audio_meta.title}")
                
                logger.info(f"使用 {self.asr_provider} 转写...")
                transcript = await self._transcribe_audio(audio_meta.file_path)
            else:
                logger.info("使用平台字幕，跳过音频下载")
                # 只读取视频元信息，避免已有字幕时仍下载整段音频
                audio_meta = await asyncio.get_running_loop().run_in_executor(
                    None,
                    lambda: self.downloader.get_metadata(video_url)
                )
                logger.info(f"获取视频信息: {audio_meta.title}")

            if not transcript or not transcript.segments:
                return ["❌ 无法获取视频内容（字幕和转写均失败）"]

            logger.info(f"获取到 {len(transcript.segments)} 段转写内容")

            tags = ""
            raw_info = audio_meta.raw_info or {}
            if isinstance(raw_info.get("tags"), list):
                tags = ", ".join(raw_info["tags"])
            elif isinstance(raw_info.get("tags"), str):
                tags = raw_info["tags"]

            prompt = build_prompt(
                title=audio_meta.title,
                segments=transcript.segments,
                tags=tags,
                style=style,
                enable_link=enable_link,
                enable_summary=enable_summary,
            )

            logger.info("调用 LLM 生成总结...")
            markdown = await llm_ask_func(prompt)

            if not markdown or str(markdown).lstrip().startswith("❌"):
                logger.error(f"LLM 生成总结失败: {markdown or 'empty response'}")
                return ["❌ 总结失败"]

            if enable_link:
                video_id = extract_video_id(video_url, "bilibili")
                if video_id:
                    markdown = replace_content_markers(
                        markdown, video_id=video_id, platform="bilibili"
                    )

            if enable_split and len(markdown) > split_max_length:
                parts = self._split_markdown(markdown, split_max_length, split_by_heading)
                logger.info(f"总结已分为 {len(parts)} 段发送")
            else:
                if len(markdown) > max_length:
                    markdown = markdown[:max_length] + "\n\n...(内容过长，已截断)"
                parts = [markdown]

            self._cleanup(audio_meta.file_path)

            return parts

        except Exception as e:
            logger.error(f"总结生成失败: {e}", exc_info=True)
            return ["❌ 总结失败"]
        finally:
            try:
                if audio_meta and hasattr(audio_meta, 'file_path'):
                    self._cleanup(audio_meta.file_path)
            except Exception:
                pass

    def _split_markdown(self, markdown: str, max_length: int, by_heading: bool = True) -> List[str]:
        """
        将 Markdown 内容分段
        
        :param markdown: 原始 Markdown 内容
        :param max_length: 每段最大字符数
        :param by_heading: 是否按标题分段
        :return: 分段后的内容列表
        """
        if len(markdown) <= max_length:
            return [markdown]
        
        if by_heading:
            parts = self._split_by_heading(markdown, max_length)
            if len(parts) > 1:
                return parts
        
        return self._split_by_length(markdown, max_length)
    
    def _split_by_heading(self, markdown: str, max_length: int) -> List[str]:
        """按 ## 标题分段"""
        heading_pattern = r'\n(?=## )'
        sections = re.split(heading_pattern, markdown)
        
        result = []
        current_part = ""
        
        for section in sections:
            if not section.strip():
                continue
            
            section = section.strip()
            if section.startswith("##"):
                section = "\n" + section
            
            if len(current_part) + len(section) <= max_length:
                current_part += section
            else:
                if current_part:
                    result.append(current_part.strip())
                
                if len(section) > max_length:
                    sub_parts = self._split_by_length(section, max_length)
                    result.extend(sub_parts[:-1])
                    current_part = sub_parts[-1] if sub_parts else ""
                else:
                    current_part = section
        
        if current_part:
            result.append(current_part.strip())
        
        return result if result else [markdown[:max_length]]
    
    def _split_by_length(self, text: str, max_length: int) -> List[str]:
        """按字符数分段，优先在段落边界分割"""
        if len(text) <= max_length:
            return [text]
        
        result = []
        remaining = text
        
        while remaining:
            if len(remaining) <= max_length:
                result.append(remaining)
                break
            
            chunk = remaining[:max_length]
            
            paragraph_break = chunk.rfind('\n\n')
            line_break = chunk.rfind('\n')
            
            if paragraph_break > max_length // 2:
                split_pos = paragraph_break + 2
            elif line_break > max_length // 2:
                split_pos = line_break + 1
            else:
                sentence_end = max(
                    chunk.rfind('。'),
                    chunk.rfind('！'),
                    chunk.rfind('？'),
                    chunk.rfind('.'),
                    chunk.rfind('!'),
                    chunk.rfind('?')
                )
                if sentence_end > max_length // 2:
                    split_pos = sentence_end + 1
                else:
                    split_pos = max_length
            
            result.append(remaining[:split_pos])
            remaining = remaining[split_pos:]
        
        return result

    def _cleanup(self, file_path: str):
        """清理临时音频文件"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"已清理临时文件: {file_path}")
        except Exception as e:
            logger.warning(f"清理文件失败: {e}")
