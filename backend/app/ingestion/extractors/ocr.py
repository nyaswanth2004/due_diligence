import logging
import threading

from PIL import Image

from app.ingestion.extractors.base import BaseExtractor, ExtractionResult, PageContent

logger = logging.getLogger(__name__)


def tesseract_available() -> bool:
    try:
        import pytesseract  # noqa: PLC0415

        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


class OcrExtractor(BaseExtractor):
    """OCR for scanned PDFs and standalone images.

    Engine selection ("auto") prefers Tesseract when the system binary is
    present, otherwise falls back to RapidOCR (pure pip install).
    """

    def __init__(self, engine: str = "auto") -> None:
        self._engine_name = engine
        self._engine = None
        self._lock = threading.Lock()

    def _init_engine(self):
        from app.core.config import settings  # noqa: PLC0415

        configured = self._engine_name or settings.OCR_ENGINE
        with self._lock:
            if self._engine is not None:
                return self._engine

            want_tess = configured in ("auto", "tesseract")
            if want_tess and tesseract_available():
                import pytesseract  # noqa: PLC0415

                self._engine_name = "tesseract"
                self._engine = ("tesseract", pytesseract)
            else:
                try:
                    from rapidocr_onnxruntime import RapidOCR  # noqa: PLC0415

                    self._engine_name = "rapidocr"
                    self._engine = ("rapidocr", RapidOCR())
                except ImportError as exc:
                    raise RuntimeError(
                        "No OCR engine available. Install Tesseract on the host or "
                        "`pip install rapidocr_onnxruntime`."
                    ) from exc
            logger.info("OCR engine initialised: %s", self._engine_name)
            return self._engine

    def ocr_image(self, image: Image.Image) -> str:
        name, engine = self._init_engine()
        if name == "tesseract":
            return engine.image_to_string(image)
        return self._rapid_ocr(engine, image)

    def _rapid_ocr(self, engine, image: Image.Image) -> str:
        import numpy as np  # noqa: PLC0415

        array = np.array(image.convert("RGB"))
        result, _ = engine(array)
        if not result:
            return ""
        lines = []
        for item in result:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                text = item[1]
                if isinstance(text, str):
                    lines.append(text.strip())
        return "\n".join(lines)

    def _pdf_to_pages(self, content: bytes) -> list[PageContent]:
        import pypdfium2 as pdfium  # noqa: PLC0415

        pdf = pdfium.PdfDocument(content)
        pages: list[PageContent] = []
        for index in range(len(pdf)):
            page = pdf[index]
            bitmap = page.render(scale=200 / 72)
            pil = bitmap.to_pil()
            text = self.ocr_image(pil)
            pages.append(PageContent(page_number=index + 1, text=text.strip()))
        return pages

    def extract(self, content: bytes, filename: str) -> ExtractionResult:
        import io  # noqa: PLC0415

        if filename.lower().endswith(".pdf"):
            return ExtractionResult(
                pages=self._pdf_to_pages(content),
                metadata={"scanned": True},
            )

        with Image.open(io.BytesIO(content)) as img:
            text = self.ocr_image(img)
        return ExtractionResult(
            pages=[PageContent(page_number=1, text=text.strip())] if text.strip() else [],
            metadata={"scanned": True},
        )
