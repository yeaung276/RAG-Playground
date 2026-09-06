import os
import base64
from io import BytesIO

import pypdfium2 as pdfium
from PIL import Image
import asyncio
import threading

import httpx

from app.logger import get_logger
from app.services.retrieval.document import Block, BlockType, Document, Page
from app.services.utils.http import http_retry
from app.utils.env import require_env

logger = get_logger("services.ocr_service")

PROMPT_V15 = """Extract all text from the image.


Instructions:
- Only return the clean Markdown.
- Do not include any explanation or extra text.
- You must include all information on the page.


Formatting Rules:
- Tables: Render tables using <table>...</table> in clean HTML format.
- Equations: Render equations using LaTeX syntax with inline ($...$) and block ($$...$$).
- Images/Charts/Diagrams: Wrap any clearly defined visual areas (e.g. charts, diagrams, pictures) in:


<figure>
Describe the image's main elements (people, objects, text), note any contextual clues (place, event, culture), mention visible text and its meaning, provide deeper analysis when relevant (especially for financial charts, graphs, or documents), comment on style or architecture if relevant, then give a concise overall summary. Describe in {figure_language}.
</figure>


- Page Numbers: Wrap page numbers in <page_number>...</page_number> (e.g., <page_number>14</page_number>).
- Checkboxes: Use ☐ for unchecked and ☑ for checked boxes.
"""


_PDF_MIME = "application/pdf"
_IMAGE_MIMES = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
    "image/tiff",
    "image/bmp",
    "image/gif",
}
_MAX_CONCURRENCY = 8

# Shared across all instances so the OCR backend sees one global concurrency cap.
_sem = asyncio.Semaphore(_MAX_CONCURRENCY)

# PDFium is not thread-safe; serialize all rendering across worker threads.
_pdfium_lock = threading.Lock()


class ExtractionService:
    @staticmethod
    def kind(mime_type: str | None) -> str | None:
        """Return "pdf", "image", or None for an unsupported/unknown MIME type."""
        if mime_type is None:
            return None
        mime_type = mime_type.split(";", 1)[0].strip().lower()
        if mime_type == _PDF_MIME:
            return "pdf"
        if mime_type in _IMAGE_MIMES:
            return "image"
        return None

    @staticmethod
    def is_supported(mime_type: str | None) -> bool:
        """Whether a file with this MIME type can be OCR'd."""
        return ExtractionService.kind(mime_type) is not None

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        target_image_dim=1800,
    ):
        self.base_url = (base_url or require_env("TYPHOON_BASE_URL")).rstrip("/")
        self.api_key = api_key or require_env("TYPHOON_OCR_API_KEY")
        self.model = model or os.getenv("TYPHOON_OCR_MODEL", "typhoon-ai/typhoon-ocr-7b")
        self.dim = target_image_dim
        self.prompt = PROMPT_V15
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=httpx.Timeout(300.0, connect=10.0),
        )

    async def process(
        self, file: BytesIO, mime_type: str | None, name: str = "document"
    ) -> Document:
        kind = self.kind(mime_type)
        if kind == "pdf":
            return await self.process_pdf(file, name=name)
        if kind == "image":
            return await self.process_img(file, name=name)
        raise ValueError(f"Unsupported MIME type for OCR: {mime_type!r}")

    async def process_pdf(self, file: BytesIO, name: str = "document") -> Document:
        logger.info("Starting OCR for '%s'", name)
        images = await asyncio.to_thread(self._render_pdf, file, name)
        logger.info("Sending %d page(s) of '%s' for OCR", len(images), name)
        results = await asyncio.gather(
            *[
                self._send_ocr_request(p, page_no=i + 1, total=len(images), name=name)
                for i, p in enumerate(images)
            ]
        )
        logger.info("Completed OCR for '%s' (%d page(s))", name, len(images))
        return Document(
            source=name, pages=[self._page(i, md) for i, md in enumerate(results)]
        )

    async def process_img(self, file: BytesIO, name: str = "image") -> Document:
        logger.info("Starting OCR for image '%s'", name)
        img_b64 = await asyncio.to_thread(self._render_image, file)
        result = await self._send_ocr_request(img_b64, name=name)
        logger.info("Completed OCR for image '%s'", name)
        return Document(source=name, pages=[self._page(0, result)])

    @staticmethod
    def _page(index: int, markdown: str) -> Page:
        return Page(
            index=index,
            markdown=markdown,
            blocks=[Block(type=BlockType.TEXT, content=markdown)],
        )

    def _render_pdf(self, file: BytesIO, name: str = "document") -> list[str]:
        with _pdfium_lock:
            pdf = pdfium.PdfDocument(file)
            try:
                total = len(pdf)
                logger.info("Rendering '%s' (%d page(s))", name, total)
                out = []
                for i, page in enumerate(pdf):
                    logger.info("Rendering page %d of %d for '%s'", i + 1, total, name)
                    # TODO: try to extract text layer first, if it give nothing or has tables, only then, apply OCR.
                    scale = self.dim / max(page.get_size())
                    img = page.render(scale=scale).to_pil()
                    out.append(self._to_b64_jpeg(img))
                    page.close()
                return out
            finally:
                pdf.close()

    def _render_image(self, file: BytesIO) -> str:
        img = Image.open(file)
        w, h = img.size
        if max(w, h) > self.dim:
            scale = self.dim / max(w, h)
            img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
        return self._to_b64_jpeg(img)

    def _to_b64_jpeg(self, img: Image.Image) -> str:
        buf = BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=90)
        return base64.b64encode(buf.getvalue()).decode()

    async def _send_ocr_request(
        self, img_b64: str, page_no: int = 1, total: int = 1, name: str = "document"
    ) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self.prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
                        },
                    ],
                }
            ],
            "max_tokens": 16384,
            "repetition_penalty": 1.1,
            "temperature": 0.1,
            "top_p": 0.6,
        }
        async with _sem:
            return await self._post_with_retry(payload, page_no, total, name)

    @http_retry(logger)
    async def _post_with_retry(
        self, payload: dict, page_no: int, total: int, name: str
    ) -> str:
        logger.info(
            "Sending OCR request for page %d of %d of '%s'", page_no, total, name
        )
        r = await self.client.post(f"{self.base_url}/chat/completions", json=payload)
        r.raise_for_status()
        logger.info(
            "Received OCR response for page %d of %d of '%s'", page_no, total, name
        )
        return r.json()["choices"][0]["message"]["content"]
