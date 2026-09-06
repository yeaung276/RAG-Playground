"""`main.py extract` — OCR-extract PDFs in a folder to JSON. Thin entrypoint."""
import asyncio
from pathlib import Path


def add_arguments(p):
    p.add_argument("folder", help="folder containing PDFs")
    p.add_argument("output", help="destination folder for extracted JSON")
    p.add_argument("-r", "--recursive", action="store_true",
                   help="recurse into subfolders")


def run(args):
    from commands.eval_utils.extract.extractor import extract_folder

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    asyncio.run(extract_folder(Path(args.folder), output, args.recursive))
