import zipfile
from typing import BinaryIO

# OS metadata that rides along in archives: macOS (__MACOSX/, ._*, .DS_Store),
# Windows (Thumbs.db, desktop.ini) and any other hidden file or folder.
_JUNK_NAMES = {"thumbs.db", "desktop.ini"}


def is_junk(name: str) -> bool:
    parts = name.rstrip("/").split("/")
    return (
        name.endswith("/")
        or any(part.startswith((".", "__MACOSX")) for part in parts)
        or parts[-1].lower() in _JUNK_NAMES
    )


def decode_text(data: bytes) -> str | None:
    """The bytes as text, or None if they are binary (not UTF-8, or carry NULs)."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None
    return None if "\x00" in text else text


def read_text_files(archive: BinaryIO) -> list[tuple[str, str]]:
    """(name, text) for every real text file in a zip; junk and binaries are skipped."""
    with zipfile.ZipFile(archive) as zf:
        files = ((name, decode_text(zf.read(name))) for name in zf.namelist() if not is_junk(name))
        return [(name, text) for name, text in files if text is not None]
