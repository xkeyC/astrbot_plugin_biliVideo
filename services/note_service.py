import asyncio
import os
import re
from typing import Optional, List

from astrbot.api import logger

from ..downloaders.bilibili_downloader import BilibiliDownloader
from ..transcriber.bcut import BcutTranscriber
from ..gpt.prompt_builder import build_prompt
from ..utils.note_helper import replace_content_markers
from ..utils.url_parser import extract_video_id


class NoteService:
    """
    总结生成服务

    流程: 下载音频 → 获取字幕/转写 → LLM 总结 → 后处理 → 返回 Markdown
    """

    def __init__(self, data_dir: str, cookies: Optional[dict] = None):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.downloader = BilibiliDownloader(
            data_dir=os.path.join(data_dir, "audio"),
            cookies=cookies,
        )
        self.transcriber = BcutTranscriber()

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

            # 2. 如果没有平台字幕，才下载音频并使用 bcut 转写
            if not transcript or not transcript.segments:
                logger.info("无平台字幕，开始下载音频并转写...")
                audio_meta = await asyncio.get_running_loop().run_in_executor(
                    None,
                    lambda: self.downloader.download(video_url, quality=quality)
                )
                logger.info(f"音频下载完成: {audio_meta.title}")
                
                logger.info("使用必剪转写...")
                transcript = await asyncio.get_running_loop().run_in_executor(
                    None,
                    lambda: self.transcriber.transcript(audio_meta.file_path)
                )
            else:
                logger.info("使用平台字幕，跳过音频下载")
                # 需要下载音频以获取视频元信息
                audio_meta = await asyncio.get_running_loop().run_in_executor(
                    None,
                    lambda: self.downloader.download(video_url, quality=quality)
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

            if not markdown:
                return ["❌ LLM 生成总结失败"]

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
            return [f"❌ 总结生成失败: {str(e)}"]
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
