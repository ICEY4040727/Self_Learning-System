"""教材 OCR：优先 Tesseract；本机未安装 tesseract 时回退 RapidOCR（ONNX）。

- **Tesseract**：https://github.com/tesseract-ocr/tesseract （需系统包
  ``tesseract-ocr``、``tesseract-ocr-chi-sim``、``tesseract-ocr-eng``）
- **RapidOCR**：https://github.com/RapidAI/RapidOCR （``rapidocr-onnxruntime``，
  ``pip install`` 即可，首次推理会下载 ONNX 模型到用户缓存目录）

可选环境变量：

- ``TESSERACT_CMD``：tesseract 可执行文件路径。
- ``TEXTBOOK_OCR_MAX_PAGES``：扫描版 PDF 最多 OCR 的页数（默认 40）。
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

OCR_LANG_DEFAULT = "chi_sim+eng"
OCR_RENDER_DPI = 200
MAX_IMAGE_SIDE = 2800
MAX_OCR_PDF_PAGES = int(os.environ.get("TEXTBOOK_OCR_MAX_PAGES", "40"))

_rapid_engine: Any = None


def _configure_tesseract_cmd() -> None:
    cmd = os.environ.get("TESSERACT_CMD")
    if not cmd:
        return
    import pytesseract

    pytesseract.pytesseract.tesseract_cmd = cmd


def _text_from_rapid_ocr_result(result: object) -> str:
    """将 RapidOCR 的 ``result`` 规范为纯文本。"""
    if not result:
        return ""
    lines: list[str] = []
    for item in result:
        try:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                txt_part = item[1]
                if isinstance(txt_part, (list, tuple)) and len(txt_part) >= 1:
                    text = str(txt_part[0])
                elif isinstance(txt_part, str):
                    text = txt_part
                else:
                    continue
            else:
                continue
            text = text.strip()
            if text:
                lines.append(text)
        except (IndexError, TypeError, ValueError):
            continue
    return "\n".join(lines).strip()


def _get_rapid_ocr_engine():
    global _rapid_engine
    if _rapid_engine is not None:
        return _rapid_engine
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as e:
        raise RuntimeError(
            "未检测到 Tesseract，且未安装 rapidocr-onnxruntime。"
            "请任选其一：\n"
            "  • Debian/Ubuntu: sudo apt install -y tesseract-ocr "
            "tesseract-ocr-chi-sim tesseract-ocr-eng\n"
            "  • 或仅 pip: pip install rapidocr-onnxruntime（首次 OCR 会下载模型）",
        ) from e
    _rapid_engine = RapidOCR()
    return _rapid_engine


def _ocr_pil_rapidocr(image) -> str:
    import numpy as np

    arr = np.array(image.convert("RGB"))
    engine = _get_rapid_ocr_engine()
    result, _elapse = engine(arr)
    return _text_from_rapid_ocr_result(result)


def ocr_pil_image(image) -> str:
    """对单张 PIL 图像做 OCR：先试 Tesseract，不可用时用 RapidOCR。"""
    try:
        import pytesseract
    except ImportError:
        logger.info("pytesseract 未安装，使用 RapidOCR")
        return _ocr_pil_rapidocr(image)

    _configure_tesseract_cmd()

    try:
        raw = pytesseract.image_to_string(image, lang=OCR_LANG_DEFAULT)
        return (raw or "").strip()
    except pytesseract.TesseractNotFoundError:
        logger.info("Tesseract 可执行文件未找到，回退 RapidOCR (ONNX)")
        return _ocr_pil_rapidocr(image)


def _pil_from_fitz_pixmap(pix) -> "object":
    from PIL import Image

    if pix.n == 1:
        mode = "L"
    elif pix.n == 3:
        mode = "RGB"
    else:
        mode = "RGBA"
    img = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
    if mode in ("RGBA", "L"):
        img = img.convert("RGB")
    return img


def _downscale_if_huge(img: "object") -> "object":
    from PIL import Image

    w, h = img.size
    m = max(w, h)
    if m <= MAX_IMAGE_SIDE:
        return img
    scale = MAX_IMAGE_SIDE / m
    nw, nh = int(w * scale), int(h * scale)
    return img.resize((nw, nh), Image.Resampling.LANCZOS)


def ocr_fitz_page(page) -> str:
    """将 PDF 单页渲染为位图后 OCR（用于无文字层的扫描页）。"""
    pix = page.get_pixmap(dpi=OCR_RENDER_DPI, alpha=False)
    try:
        img = _pil_from_fitz_pixmap(pix)
    finally:
        del pix
    img = _downscale_if_huge(img)
    return ocr_pil_image(img)


def ocr_image_bytes(content: bytes) -> str:
    """识别常见图片格式（PNG / JPEG / WebP / GIF 首帧等）。"""
    import io

    from PIL import Image, UnidentifiedImageError

    try:
        im = Image.open(io.BytesIO(content))
    except UnidentifiedImageError as e:
        raise RuntimeError("无法识别的图片格式") from e

    with im:
        im.load()
        if getattr(im, "n_frames", 1) > 1:
            im.seek(0)
        img = im.convert("RGB")
    img = _downscale_if_huge(img)
    return ocr_pil_image(img)
