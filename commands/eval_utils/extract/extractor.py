"""OCR-extract every PDF in a folder to one JSON per file.

Output shape matches what the RAG corpus loader reads:
`{filename, chunks:[{seq, content}]}`. Already-extracted files are skipped, so
runs are resumable. Extraction is bounded to CONCURRENCY at a time.
"""
import asyncio
import json
from io import BytesIO
from pathlib import Path

from tqdm.asyncio import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm

from app.logger import get_logger
from app.services.retrieval import extraction_service

logger = get_logger(__name__)

CONCURRENCY = 4


async def extract_folder(folder: Path, output: Path, recursive: bool) -> None:
    ocr = extraction_service.ExtractionService()
    semaphore = asyncio.Semaphore(CONCURRENCY)
    globber = folder.rglob if recursive else folder.glob
    pdfs = sorted(p for p in globber("*") if p.is_file() and p.suffix.lower() == ".pdf")

    todo = [p for p in pdfs if not (output / f"{p.stem}.json").exists()]
    done = len(pdfs) - len(todo)
    logger.info("Found %d PDF(s), %d already done, %d to do", len(pdfs), done, len(todo))
    if not todo:
        return

    with logging_redirect_tqdm():
        await tqdm.gather(
            *(_extract_pdf(ocr, semaphore, p, output) for p in todo),
            total=len(pdfs),
            initial=done,
            desc="OCR",
            unit="pdf",
        )


async def _extract_pdf(ocr, semaphore, path: Path, output: Path) -> None:
    async with semaphore:
        buf = BytesIO(path.read_bytes())
        document = await ocr.process(buf, "application/pdf", name=path.name)
    doc = {
        "filename": path.name,
        "chunks": [{"seq": p.index, "content": p.markdown} for p in document.pages],
    }
    (output / f"{path.stem}.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8"
    )
