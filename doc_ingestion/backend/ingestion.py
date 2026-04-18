import os
from dataclasses import dataclass

from fastapi import UploadFile


@dataclass
class FileMetadata:
    filename: str
    file_type: str
    size_bytes: int


async def read_upload(file: UploadFile) -> tuple[bytes, FileMetadata]:
    content = await file.read()
    ext = os.path.splitext(file.filename or "")[-1].lower()
    return content, FileMetadata(
        filename=file.filename or "unknown",
        file_type=ext or "unknown",
        size_bytes=len(content),
    )
