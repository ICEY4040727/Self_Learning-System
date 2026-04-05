"""
services/text_extraction.py
──────────────────────────────────────────────────────────────
多格式教材文本提取服务

支持格式：
  .txt / .md  → 直接 decode
  .pdf        → pdfplumber（逐页提取，保留段落换行）
  .docx       → python-docx（段落遍历）
  .doc        → 降级提示（需 LibreOffice/antiword，不强依赖）

依赖安装（requirements.txt 追加）：
  pdfplumber>=0.10.0
  python-docx>=1.1.0

错误策略：
  - 每种提取器内部 try/except，失败返回 ExtractionError
  - 调用方负责将错误写入 CourseMaterial.error_message
──────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ExtractionError(Exception):
    """提取失败时抛出，携带人可读的错误描述。"""


# ── Plain text / Markdown ────────────────────────────────────

def extract_text(content_bytes: bytes, content_type: str, filename: str) -> str:
    """
    根据 content_type 派发到对应提取器。
    返回清洗后的纯文本字符串。
    抛出 ExtractionError 表示提取失败。
    """
    ct = content_type.lower().split(";")[0].strip()

    if ct in ("text/plain", "text/markdown"):
        return _extract_plaintext(content_bytes, filename)

    if ct == "application/pdf":
        return _extract_pdf(content_bytes, filename)

    if ct in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    ):
        return _extract_docx(content_bytes, filename)

    raise ExtractionError(
        f"不支持的文件类型 '{ct}'。"
        "请上传 .txt / .md / .pdf / .docx 格式。"
    )


def _extract_plaintext(data: bytes, filename: str) -> str:
    for enc in ("utf-8", "utf-8-sig", "gbk", "big5"):
        try:
            text = data.decode(enc)
            return _clean(text)
        except UnicodeDecodeError:
            continue
    raise ExtractionError(
        f"无法解码文件 '{filename}'，请确保使用 UTF-8 或 GBK 编码。"
    )


def _extract_pdf(data: bytes, filename: str) -> str:
    try:
        import pdfplumber
    except ImportError:
        raise ExtractionError(
            "服务端缺少 pdfplumber 依赖，请联系管理员安装：pip install pdfplumber"
        )

    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            pages: list[str] = []
            for i, page in enumerate(pdf.pages):
                text = page.extract_text(x_tolerance=3, y_tolerance=3)
                if text:
                    pages.append(text.strip())
                else:
                    logger.warning("PDF 第 %d 页无可提取文字（可能为扫描图片）", i + 1)

        if not pages:
            raise ExtractionError(
                f"'{filename}' 为纯图片 PDF，无法提取文字。"
                "请提供文字版 PDF 或转为 DOCX/TXT。"
            )
        return _clean("\n\n".join(pages))

    except ExtractionError:
        raise
    except Exception as exc:
        raise ExtractionError(f"PDF 解析失败：{exc}") from exc


def _extract_docx(data: bytes, filename: str) -> str:
    try:
        from docx import Document
    except ImportError:
        raise ExtractionError(
            "服务端缺少 python-docx 依赖，请联系管理员安装：pip install python-docx"
        )

    try:
        doc = Document(io.BytesIO(data))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        if not paragraphs:
            raise ExtractionError(f"'{filename}' 文档内容为空或仅包含非文字元素。")
        return _clean("\n\n".join(paragraphs))

    except ExtractionError:
        raise
    except Exception as exc:
        raise ExtractionError(f"DOCX 解析失败：{exc}") from exc


def _clean(text: str) -> str:
    """
    基础文本清洗：
    - 合并超过 3 个连续换行 → 2 个换行（保留段落结构）
    - 去除行尾空白
    - 去除 BOM / 零宽字符
    """
    import re
    # 去除零宽字符
    text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)
    # 去除行尾空白
    text = "\n".join(line.rstrip() for line in text.splitlines())
    # 折叠多余空行
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ── Utility ───────────────────────────────────────────────────

def estimate_token_count(text: str) -> int:
    """粗估 token 数（中文约 1.5 字/token，英文约 4 字/token）。"""
    import re
    cjk_count  = len(re.findall(r"[\u4e00-\u9fff\u3400-\u4dbf]", text))
    ascii_count = len(re.findall(r"[a-zA-Z0-9]", text))
    return int(cjk_count / 1.5 + ascii_count / 4)


def truncate_to_token_limit(text: str, max_tokens: int = 60_000) -> tuple[str, bool]:
    """
    粗截断到 max_tokens 以内。
    返回 (截断后文本, 是否发生截断)。
    """
    estimated = estimate_token_count(text)
    if estimated <= max_tokens:
        return text, False

    # 按字符比例估算截断点
    ratio = max_tokens / estimated
    cutoff = int(len(text) * ratio * 0.95)  # 留 5% 安全边距

    # 尽量在段落边界截断
    idx = text.rfind("\n\n", 0, cutoff)
    if idx == -1:
        idx = cutoff

    return text[:idx] + "\n\n[内容因长度限制被截断]", True
