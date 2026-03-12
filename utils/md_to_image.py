import base64
import logging
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)

_ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
_LOGO_PATH = os.path.join(_ASSETS_DIR, "logo.png")
_FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "fonts")

_FONT_MAP = {
    "SourceHanSansSC-Light.otf": ("Source Han Sans SC", "300"),
    "SourceHanSansSC-Regular.otf": ("Source Han Sans SC", "400"),
    "SourceHanSansSC-Bold.otf": ("Source Han Sans SC", "700"),
}

_font_face_cache: Optional[str] = None


def _build_font_faces() -> str:
    global _font_face_cache
    if _font_face_cache is not None:
        return _font_face_cache

    faces = []
    for filename, (family, weight) in _FONT_MAP.items():
        path = os.path.join(_FONTS_DIR, filename)
        if not os.path.exists(path):
            logger.warning(f"字体文件不存在: {path}")
            continue
        try:
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            font_format = "opentype" if filename.endswith(".otf") else "truetype"
            faces.append(
                f"@font-face{{font-family:'{family}';font-weight:{weight};"
                f"font-display:swap;"
                f"src:url(data:font/{font_format};base64,{b64}) format('{font_format}')}}"
            )
        except Exception as e:
            logger.warning(f"读取字体 {filename} 失败: {e}")

    _font_face_cache = "\n".join(faces)
    return _font_face_cache


CARD_COLORS = [
    ('#60a5fa', 'rgba(96,165,250,.10)'),
    ('#34d399', 'rgba(52,211,153,.10)'),
    ('#a78bfa', 'rgba(167,139,250,.10)'),
    ('#fb923c', 'rgba(251,146,60,.10)'),
    ('#22d3ee', 'rgba(34,211,238,.10)'),
    ('#f472b6', 'rgba(244,114,182,.10)'),
]


def _get_logo_base64() -> str:
    if os.path.exists(_LOGO_PATH):
        try:
            with open(_LOGO_PATH, 'rb') as f:
                return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
        except Exception:
            pass
    return ""


def _wrap_sections_in_cards(html: str) -> str:
    parts = re.split(r'(<h2[^>]*>.*?</h2>)', html, flags=re.DOTALL | re.IGNORECASE)

    if len(parts) <= 1:
        return f'<div class="card card-0">{html}</div>'

    result = []
    card_idx = 0

    before_first_h2 = parts[0].strip()
    if before_first_h2:
        result.append(f'<div class="card-intro">{before_first_h2}</div>')

    i = 1
    while i < len(parts):
        h2_tag = parts[i] if i < len(parts) else ''
        content = parts[i + 1] if i + 1 < len(parts) else ''
        color_idx = card_idx % len(CARD_COLORS)
        border_color, bg_color = CARD_COLORS[color_idx]

        result.append(
            f'<div class="card card-{color_idx}" '
            f'style="border-left-color:{border_color};background:{bg_color}">'
            f'{h2_tag}{content}</div>'
        )
        card_idx += 1
        i += 2

    return '\n'.join(result)


def _build_full_html(body_html: str, logo_uri: str, title_text: str = '', footer_time: str = '', is_mobile: bool = False) -> str:
    font_faces = _build_font_faces()

    if is_mobile:
        return _build_mobile_html(font_faces, body_html, title_text, footer_time)

    return f'''<!DOCTYPE html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
{font_faces}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{
  font-family:'Source Han Sans SC','Noto Sans SC','Microsoft YaHei','PingFang SC',sans-serif;
  background:#1a1b2e;
  color:#c9cedc;
  width:1400px;
  line-height:1.85;
  font-size:15px;
}}

.header{{
  background:linear-gradient(135deg,#1e2140 0%,#252250 30%,#1a2744 70%,#1e2140 100%);
  padding:40px 56px 32px;
  border-bottom:2px solid rgba(139,92,246,.25);
  position:relative;
  overflow:hidden;
  text-align:center;
}}
.header::before{{
  content:'';position:absolute;top:0;left:0;right:0;bottom:0;
  background:radial-gradient(ellipse at 70% 0%,rgba(96,165,250,.14) 0%,transparent 55%),
             radial-gradient(ellipse at 30% 100%,rgba(139,92,246,.12) 0%,transparent 55%);
  pointer-events:none;
}}
.header h1{{
  position:relative;z-index:1;
  font-size:28px;font-weight:800;color:#f1f5f9;margin:0 auto;
  line-height:1.4;letter-spacing:.5px;
  background:linear-gradient(90deg,#e2e8f0 0%,#93c5fd 50%,#c4b5fd 100%);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  background-clip:text;
  max-width:90%;
}}
.header-line{{
  position:relative;z-index:1;
  width:80px;height:3px;margin:14px auto 0;
  background:linear-gradient(90deg,#60a5fa,#8b5cf6);
  border-radius:2px;
}}

.content{{
  padding:28px 40px 20px;
  display:grid;
  grid-template-columns:1fr 1fr;
  gap:20px;
  align-items:start;
}}

.card,.card-intro{{
  background:rgba(30,33,64,.65);
  border-radius:12px;
  border:1px solid rgba(148,163,184,.08);
  border-left:4px solid #60a5fa;
  padding:20px 24px;
  box-shadow:0 2px 8px rgba(0,0,0,.2);
  backdrop-filter:blur(8px);
}}
.card-intro{{
  grid-column:1 / -1;
  border-left-color:#a5f3c4;
  background:rgba(52,211,153,.06);
}}
.card-full{{
  grid-column:1 / -1;
}}

h1{{font-size:22px;font-weight:700;color:#e2e8f0;margin-bottom:12px}}
h2{{
  font-size:16px;font-weight:700;color:#e2e8f0;
  margin:-20px -24px 14px;
  padding:12px 24px 10px;
  border-radius:12px 12px 0 0;
  background:rgba(0,0,0,.18);
  border-bottom:1px solid rgba(148,163,184,.08);
  display:flex;align-items:center;gap:8px;
  letter-spacing:.3px;
}}
h2::before{{
  content:'';display:inline-block;width:8px;height:8px;border-radius:50%;
  background:currentColor;opacity:.6;flex-shrink:0;
}}
h3{{font-size:15px;font-weight:700;color:#93c5fd;margin-top:16px;margin-bottom:8px;
    padding-left:12px;border-left:3px solid rgba(96,165,250,.4)}}
h4,h5,h6{{font-size:14px;font-weight:600;color:#c4b5fd;margin-top:12px;margin-bottom:6px}}

p{{margin-bottom:10px;text-align:justify;word-break:break-word;font-size:14px}}
strong{{color:#f9a8d4;font-weight:700}}
em{{color:#67e8f9;font-style:italic}}

.ts{{display:inline-block;background:rgba(251,146,30,.15);color:#fb923c;font-weight:700;
     font-size:11px;padding:2px 8px;border-radius:10px;border:1px solid rgba(251,146,30,.3);
     margin:0 2px;font-family:'JetBrains Mono',monospace;letter-spacing:.5px}}

ul,ol{{margin-bottom:10px;padding-left:20px}}
li{{margin-bottom:5px;line-height:1.7;padding-left:4px;font-size:14px}}
li::marker{{color:#60a5fa;font-weight:700}}

blockquote{{
  background:rgba(139,92,246,.08);
  border-left:3px solid #8b5cf6;
  border-radius:0 10px 10px 0;
  padding:12px 18px;
  margin:12px 0;
  color:#a5b4fc;
  box-shadow:0 2px 6px rgba(139,92,246,.08);
}}
blockquote p{{margin-bottom:4px}}

code{{background:rgba(248,113,113,.1);color:#fca5a5;padding:2px 6px;border-radius:6px;
      font-size:13px;font-family:'JetBrains Mono',monospace}}
pre{{background:#12132a;color:#e2e8f0;padding:12px 16px;border-radius:10px;margin:10px 0;
     font-size:13px;line-height:1.5;border:1px solid rgba(148,163,184,.1);
     box-shadow:inset 0 1px 4px rgba(0,0,0,.3)}}
pre code{{background:transparent;color:inherit;padding:0}}

hr{{border:none;height:1px;
    background:linear-gradient(to right,transparent,rgba(148,163,184,.2),transparent);
    margin:16px 0}}

table{{width:100%;border-collapse:collapse;margin:10px 0;border-radius:8px;overflow:hidden}}
th{{background:rgba(96,165,250,.12);color:#93c5fd;font-weight:700;padding:8px 12px;
    text-align:left;border-bottom:2px solid rgba(96,165,250,.2);font-size:14px}}
td{{padding:6px 12px;border-bottom:1px solid rgba(148,163,184,.08);font-size:14px}}
tr:nth-child(even) td{{background:rgba(148,163,184,.03)}}

.footer{{
  padding:14px 40px;
  border-top:1px solid rgba(148,163,184,.1);
  display:flex;align-items:center;justify-content:space-between;
  background:rgba(0,0,0,.1);
}}
.footer .flogo{{width:22px;height:22px;border-radius:6px;object-fit:cover;opacity:.7}}
.footer .flogo-e{{font-size:16px;opacity:.7}}
.ftxt{{font-size:11px;color:#64748b;letter-spacing:.8px;font-family:'JetBrains Mono',monospace}}
.ftxt .br{{color:#94a3b8;font-weight:600}}
.ftime{{font-size:11px;color:#4a5568;letter-spacing:.5px;font-family:'JetBrains Mono',monospace}}
</style></head>
<body>
<div class="header">
  <h1>{title_text}</h1>
  <div class="header-line"></div>
</div>
<div class="content">
{body_html}
</div>
<div class="footer">
  <div class="ftxt">Powered by <span class="br">biliVideo+</span> xkeyC Fork</div>
  <div class="ftime">{footer_time}</div>
</div>
</body></html>'''


def _build_mobile_html(font_faces: str, body_html: str, title_text: str, footer_time: str) -> str:
    return f'''<!DOCTYPE html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<style>
{font_faces}
*{{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}}
html{{font-size:16px}}
body{{
  font-family:'Source Han Sans SC','Noto Sans SC','Microsoft YaHei','PingFang SC',sans-serif;
  background:#1a1b2e;
  color:#c9cedc;
  width:750px;
  line-height:1.8;
  font-size:16px;
  -webkit-font-smoothing:antialiased;
}}

.header{{
  background:linear-gradient(135deg,#1e2140 0%,#252250 30%,#1a2744 70%,#1e2140 100%);
  padding:32px 24px 24px;
  border-bottom:2px solid rgba(139,92,246,.25);
  position:relative;
  overflow:hidden;
  text-align:center;
}}
.header::before{{
  content:'';position:absolute;top:0;left:0;right:0;bottom:0;
  background:radial-gradient(ellipse at 70% 0%,rgba(96,165,250,.14) 0%,transparent 55%),
             radial-gradient(ellipse at 30% 100%,rgba(139,92,246,.12) 0%,transparent 55%);
  pointer-events:none;
}}
.header h1{{
  position:relative;z-index:1;
  font-size:22px;font-weight:800;color:#f1f5f9;margin:0 auto;
  line-height:1.5;letter-spacing:.3px;
  background:linear-gradient(90deg,#e2e8f0 0%,#93c5fd 50%,#c4b5fd 100%);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  background-clip:text;
  max-width:95%;
}}
.header-line{{
  position:relative;z-index:1;
  width:60px;height:3px;margin:12px auto 0;
  background:linear-gradient(90deg,#60a5fa,#8b5cf6);
  border-radius:2px;
}}

.content{{
  padding:20px 16px 16px;
  display:flex;
  flex-direction:column;
  gap:16px;
}}

.card,.card-intro{{
  background:rgba(30,33,64,.65);
  border-radius:16px;
  border:1px solid rgba(148,163,184,.08);
  border-left:5px solid #60a5fa;
  padding:18px 20px;
  box-shadow:0 2px 10px rgba(0,0,0,.25);
  backdrop-filter:blur(8px);
}}
.card-intro{{
  border-left-color:#a5f3c4;
  background:rgba(52,211,153,.06);
}}

h1{{font-size:20px;font-weight:700;color:#e2e8f0;margin-bottom:10px}}
h2{{
  font-size:17px;font-weight:700;color:#e2e8f0;
  margin:-18px -20px 14px;
  padding:14px 20px 12px;
  border-radius:16px 16px 0 0;
  background:rgba(0,0,0,.18);
  border-bottom:1px solid rgba(148,163,184,.08);
  display:flex;align-items:center;gap:10px;
  letter-spacing:.2px;
  min-height:48px;
}}
h2::before{{
  content:'';display:inline-block;width:10px;height:10px;border-radius:50%;
  background:currentColor;opacity:.6;flex-shrink:0;
}}
h3{{font-size:16px;font-weight:700;color:#93c5fd;margin-top:16px;margin-bottom:8px;
    padding-left:12px;border-left:3px solid rgba(96,165,250,.4)}}
h4,h5,h6{{font-size:15px;font-weight:600;color:#c4b5fd;margin-top:12px;margin-bottom:6px}}

p{{margin-bottom:12px;text-align:justify;word-break:break-word;font-size:16px;line-height:1.8}}
strong{{color:#f9a8d4;font-weight:700}}
em{{color:#67e8f9;font-style:italic}}

.ts{{
  display:inline-flex;align-items:center;
  background:rgba(251,146,30,.15);color:#fb923c;font-weight:700;
  font-size:14px;padding:4px 10px;border-radius:12px;border:1px solid rgba(251,146,30,.3);
  margin:2px 4px;font-family:'JetBrains Mono',monospace;letter-spacing:.3px;
  min-height:28px;
}}

ul,ol{{margin-bottom:12px;padding-left:24px}}
li{{margin-bottom:8px;line-height:1.75;padding-left:4px;font-size:16px}}
li::marker{{color:#60a5fa;font-weight:700}}

blockquote{{
  background:rgba(139,92,246,.08);
  border-left:4px solid #8b5cf6;
  border-radius:0 12px 12px 0;
  padding:14px 18px;
  margin:14px 0;
  color:#a5b4fc;
  box-shadow:0 2px 8px rgba(139,92,246,.08);
}}
blockquote p{{margin-bottom:4px}}

code{{background:rgba(248,113,113,.1);color:#fca5a5;padding:3px 8px;border-radius:8px;
      font-size:15px;font-family:'JetBrains Mono',monospace}}
pre{{background:#12132a;color:#e2e8f0;padding:14px 16px;border-radius:12px;margin:12px 0;
     font-size:14px;line-height:1.6;border:1px solid rgba(148,163,184,.1);
     box-shadow:inset 0 1px 4px rgba(0,0,0,.3);
     overflow-x:auto;-webkit-overflow-scrolling:touch}}
pre code{{background:transparent;color:inherit;padding:0}}

hr{{border:none;height:1px;
    background:linear-gradient(to right,transparent,rgba(148,163,184,.2),transparent);
    margin:18px 0}}

table{{width:100%;border-collapse:collapse;margin:12px 0;border-radius:10px;overflow:hidden}}
th{{background:rgba(96,165,250,.12);color:#93c5fd;font-weight:700;padding:10px 14px;
    text-align:left;border-bottom:2px solid rgba(96,165,250,.2);font-size:15px}}
td{{padding:10px 14px;border-bottom:1px solid rgba(148,163,184,.08);font-size:15px}}
tr:nth-child(even) td{{background:rgba(148,163,184,.03)}}

.footer{{
  padding:16px 20px;
  border-top:1px solid rgba(148,163,184,.1);
  display:flex;align-items:center;justify-content:space-between;
  background:rgba(0,0,0,.1);
}}
.footer .flogo{{width:20px;height:20px;border-radius:6px;object-fit:cover;opacity:.7}}
.ftxt{{font-size:12px;color:#64748b;letter-spacing:.5px;font-family:'JetBrains Mono',monospace}}
.ftxt .br{{color:#94a3b8;font-weight:600}}
.ftime{{font-size:12px;color:#4a5568;letter-spacing:.3px;font-family:'JetBrains Mono',monospace}}
</style></head>
<body>
<div class="header">
  <h1>{title_text}</h1>
  <div class="header-line"></div>
</div>
<div class="content">
{body_html}
</div>
<div class="footer">
  <div class="ftxt">Powered by <span class="br">biliVideo+</span> xkeyC Fork</div>
  <div class="ftime">{footer_time}</div>
</div>
</body></html>'''


def _highlight_timestamps(html: str) -> str:
    html = re.sub(r'⏱\s*(\d{1,2}:\d{2})', r'<span class="ts">⏱ \1</span>', html)
    html = re.sub(r'\[(\d{1,2}:\d{2})\]', r'<span class="ts">⏱ \1</span>', html)
    html = re.sub(
        r'(</h2>\s*)'
        r'<p>\s*<span class="ts">[^<]*</span>\s*\*?\s*</p>',
        r'\1',
        html
    )
    return html


def _extract_title(html: str) -> tuple:
    m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.DOTALL | re.IGNORECASE)
    if m:
        title_text = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        html = html[:m.start()] + html[m.end():]
        clean_title = re.sub(r'[📑📝🎬🎥\s]', '', title_text)
        if clean_title:
            dup_pattern = r'<p[^>]*>[^<]*' + re.escape(clean_title[:20]) + r'[^<]*</p>'
            html = re.sub(dup_pattern, '', html, count=1)
        if ' - ' in title_text:
            parts = title_text.rsplit(' - ', 1)
            title_text = f"{parts[0]} —— {parts[1]}"
        return title_text, html
    return 'AI 视频总结', html


async def render_note_image_async(
    markdown_text: str,
    output_path: str,
    width: int = 1400,
    is_mobile: bool = False,
    timeout: int = 60000,
) -> Optional[str]:
    try:
        import markdown as md
    except ImportError as e:
        logger.error(f"缺少依赖: {e}. 请安装: pip install markdown")
        return None

    try:
        from .browser import render_html_to_image
    except ImportError:
        from browser import render_html_to_image

    try:
        import time as _time
        from datetime import datetime
        render_start = _time.time()

        html_body = md.markdown(
            markdown_text,
            extensions=['tables', 'fenced_code', 'nl2br'],
        )
        html_body = _highlight_timestamps(html_body)

        title_text, html_body = _extract_title(html_body)

        html_body = _wrap_sections_in_cards(html_body)

        logo_uri = _get_logo_base64()

        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        footer_time = f"{now_str}"

        actual_width = 750 if is_mobile else width
        full_html = _build_full_html(html_body, logo_uri, title_text, footer_time, is_mobile)

        screenshot_bytes = await render_html_to_image(
            html_content=full_html,
            selector="body",
            width=actual_width,
            scale_factor=2,
            is_mobile=is_mobile,
            full_page=True,
            timeout=timeout,
        )

        if not screenshot_bytes:
            logger.error("Playwright 渲染失败")
            return None

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(screenshot_bytes)

        if os.path.exists(output_path):
            render_secs = round(_time.time() - render_start, 1)
            logger.info(f"总结图片已生成: {output_path} ({os.path.getsize(output_path)} bytes, 渲染{render_secs}s)")
            return output_path
        else:
            logger.error("图片文件未生成")
            return None

    except Exception as e:
        logger.error(f"渲染总结图片失败: {e}", exc_info=True)
        return None


def render_note_image(
    markdown_text: str,
    output_path: str,
    width: int = 1400,
    timeout: int = 60000,
) -> Optional[str]:
    import asyncio

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    render_note_image_async(markdown_text, output_path, width, is_mobile=False, timeout=timeout)
                )
                return future.result()
        else:
            return loop.run_until_complete(
                render_note_image_async(markdown_text, output_path, width, is_mobile=False, timeout=timeout)
            )
    except RuntimeError:
        return asyncio.run(
            render_note_image_async(markdown_text, output_path, width, is_mobile=False, timeout=timeout)
        )
