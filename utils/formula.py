"""LaTeX 公式识别与本地 MathML 转换（移植自 astrbot_plugin_markdown_killer）。

公式在 Markdown 解析前替换为占位符，避免 ``_``、``*``、``\\`` 等被 Markdown
误处理；解析完成后再换成 latex2mathml 生成的 MathML，由 Chromium 原生渲染，
不依赖 KaTeX/MathJax CDN。
"""

from __future__ import annotations

import html
import logging
import re
import xml.etree.ElementTree as ET
from typing import Callable

logger = logging.getLogger(__name__)

_BLOCK_FORMULA_RE = re.compile(
    r"(?<!\\)\\\[(?P<bracket>.+?)(?<!\\)\\\]"
    r"|(?<![$\\])\$\$(?P<dollar>.+?)(?<![$\\])\$\$(?!\$)",
    re.DOTALL,
)
_INLINE_FORMULA_RE = re.compile(
    r"(?<!\\)\\\((?P<bracket>.+?)(?<!\\)\\\)"
    r"|(?<![$\\])\$(?![\s$])(?P<dollar>.+?)(?<![\s\\])\$(?![\d$])"
)
_CODE_RE = re.compile(r"```[\s\S]*?```|~~~[\s\S]*?~~~|`+[^\n]*?`+")

FORMULA_CSS = """
.display-formula{display:flex;justify-content:center;margin:12px 0;padding:4px 0;
  overflow:hidden}
math{font-size:1.12em;vertical-align:-0.12em}
math[display="block"]{font-size:1.2em}
"""


_MATHML_NS = "http://www.w3.org/1998/Math/MathML"
_MATHML_TAGS = frozenset(
    {
        "math", "mi", "mn", "mo", "ms", "mspace", "mtext", "mrow", "mfrac",
        "msqrt", "mroot", "mstyle", "merror", "mpadded", "mphantom", "mfenced",
        "menclose", "msub", "msup", "msubsup", "munder", "mover", "munderover",
        "mmultiscripts", "mprescripts", "none", "mtable", "mtr", "mtd",
        "mlabeledtr", "maligngroup", "malignmark", "semantics", "annotation",
    }
)
ET.register_namespace("", _MATHML_NS)


_ALIGNED_ENV_RE = re.compile(
    r"\\(begin|end)\{(?:aligned|alignedat)\}(?:\[[tbc]\])?(?:\{\d+\})?"
)
_GATHERED_ENV_RE = re.compile(r"\\(begin|end)\{(?:gathered|gather\*?)\}(?:\[[tbc]\])?")


def _normalize_latex(latex: str) -> str:
    """Map environments latex2mathml flattens into ones it lays out as tables."""
    latex = _ALIGNED_ENV_RE.sub(r"\\\1{align*}", latex)
    return _GATHERED_ENV_RE.sub(
        lambda m: r"\begin{array}{c}" if m.group(1) == "begin" else r"\end{array}",
        latex,
    )


def _sanitize_mathml(mathml: str) -> str:
    """Re-serialize latex2mathml output, allowing only inert MathML.

    latex2mathml copies ``\\text{...}`` content verbatim, so ``<``/``>`` there
    could smuggle HTML elements (``<mtext>`` is an HTML integration point).
    Parsing as XML and re-serializing escapes all text; any non-MathML element
    or script/link-like attribute rejects the formula.
    """
    # latex2mathml emits alignment ``&`` (outside table environments) and
    # ``\text`` content unescaped. Drop stray alignment marks and escape bare
    # ``&``/``<`` so valid formulas parse; ``<`` + letter still fails → rejected.
    mathml = mathml.replace("<mi>&</mi>", "")
    mathml = re.sub(r"&(?!#?\w+;)", "&amp;", mathml)
    mathml = re.sub(r"<(?![A-Za-z/!?])", "&lt;", mathml)
    root = ET.fromstring(mathml)
    for element in root.iter():
        namespace, _, tag = element.tag.rpartition("}")
        if namespace not in ("", "{" + _MATHML_NS) or tag not in _MATHML_TAGS:
            raise ValueError(f"不允许的 MathML 元素: {tag}")
        for name, value in element.attrib.items():
            local_name = name.rpartition("}")[2].lower()
            lowered = value.lower()
            if (
                "}" in name
                or local_name.startswith("on")
                or local_name in ("href", "src")
                or "url(" in lowered
                or "javascript:" in lowered
            ):
                raise ValueError(f"不允许的 MathML 属性: {name}")
    return ET.tostring(root, encoding="unicode")


def _is_standalone_line(text: str, match: re.Match[str]) -> bool:
    """Return whether a block-formula match occupies its lines on its own."""
    line_start = text.rfind("\n", 0, match.start()) + 1
    line_end = text.find("\n", match.end())
    if line_end == -1:
        line_end = len(text)
    return (
        not text[line_start : match.start()].strip()
        and not text[match.end() : line_end].strip()
    )


def _overlaps_any(start: int, end: int, spans: list[tuple[int, int]]) -> bool:
    return any(start < span_end and end > span_start for span_start, span_end in spans)


def _formula_source(match: re.Match[str]) -> str:
    return match.group("bracket") or match.group("dollar") or ""


def _find_formulas(text: str) -> list[tuple[re.Match[str], bool]]:
    """返回代码区域之外的公式匹配 (match, is_block)，按出现顺序排列。"""
    code_spans = [(m.start(), m.end()) for m in _CODE_RE.finditer(text)]
    block_matches = [
        m
        for m in _BLOCK_FORMULA_RE.finditer(text)
        if not _overlaps_any(m.start(), m.end(), code_spans)
    ]
    block_spans = [(m.start(), m.end()) for m in block_matches]
    inline_matches = [
        m
        for m in _INLINE_FORMULA_RE.finditer(text)
        if not _overlaps_any(m.start(), m.end(), code_spans)
        and not _overlaps_any(m.start(), m.end(), block_spans)
    ]
    return sorted(
        [(m, True) for m in block_matches] + [(m, False) for m in inline_matches],
        key=lambda item: item[0].start(),
    )


def contains_latex_formulas(text: str) -> bool:
    return bool(_find_formulas(text))


def convert_latex(latex: str, display: bool) -> str:
    from latex2mathml.converter import convert

    mathml = convert(_normalize_latex(latex.strip()))
    if display:
        if re.search(r"<math\b[^>]*\bdisplay=", mathml):
            mathml = re.sub(
                r'(<math\b[^>]*?)\sdisplay="[^"]*"',
                r'\1 display="block"',
                mathml,
                count=1,
            )
        else:
            mathml = re.sub(r"<math(?=[\s>])", '<math display="block"', mathml, count=1)
    return _sanitize_mathml(mathml)


def markdown_with_formulas(text: str, to_html: Callable[[str], str]) -> str:
    """用 ``to_html`` 把 Markdown 转为 HTML，并将其中的 LaTeX 公式渲染为 MathML。

    缺少 latex2mathml 或单个公式转换失败时，该公式保留原始 LaTeX 文本。
    """
    formulas = _find_formulas(text)
    if not formulas:
        return to_html(text)

    token_prefix = "BILIFORMULATOKEN"
    while token_prefix in text:
        token_prefix += "X"

    parts: list[str] = []
    replacements: dict[str, str] = {}
    cursor = 0
    for index, (match, display) in enumerate(formulas):
        parts.append(text[cursor : match.start()])
        token = f"{token_prefix}{index}END"
        # 表格行、列表项或正文中的块级公式若被提成独立段落会打断原有结构
        display = display and _is_standalone_line(text, match)
        try:
            mathml = convert_latex(_formula_source(match), display=display)
        except Exception as e:
            logger.warning(f"公式转换失败，保留原文: {e}")
            parts.append(token)
            replacements[token] = html.escape(match.group(0), quote=False)
            cursor = match.end()
            continue
        if display:
            parts.append(f"\n\n{token}\n\n")
            replacements[token] = f'<div class="display-formula">{mathml}</div>'
        else:
            parts.append(token)
            replacements[token] = mathml
        cursor = match.end()
    parts.append(text[cursor:])

    rendered = to_html("".join(parts))
    for token, replacement in replacements.items():
        rendered = rendered.replace(f"<p>{token}</p>", replacement)
        rendered = rendered.replace(token, replacement)
    return rendered
