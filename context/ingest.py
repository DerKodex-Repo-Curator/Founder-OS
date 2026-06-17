"""Unified ingestion pipeline for Context Space assets."""
import asyncio
import logging
import mimetypes
import os
import threading

from memory import context_store, vector_store
from integrations import documents as doc_extract
from integrations import transcribe
from tools.scraper import scrape_url

logger = logging.getLogger(__name__)

AUDIO_EXT = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac", ".webm"}
VIDEO_EXT = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
DOC_EXT = {".pdf", ".docx", ".txt", ".md", ".markdown", ".rst", ".csv", ".json", ".pptx", ".xlsx", ".doc"}


def _chunk(text: str, size: int = 1000, overlap: int = 150) -> list:
    text = " ".join((text or "").split())
    if not text:
        return []
    chunks, i, n = [], 0, len(text)
    step = max(size - overlap, 1)
    while i < n:
        chunks.append(text[i:i + size])
        i += step
    return chunks


def detect_kind(filename: str, mime: str = "") -> str:
    name = (filename or "").lower()
    ext = os.path.splitext(name)[1]
    if ext in VIDEO_EXT or (mime or "").startswith("video/"):
        return "video"
    if ext in AUDIO_EXT or (mime or "").startswith("audio/"):
        return "audio"
    if ext in IMAGE_EXT or (mime or "").startswith("image/"):
        return "image"
    return "file"


def _extract_from_file(path: str, mime: str, filename: str) -> str:
    ext = os.path.splitext(filename or path)[1].lower()
    if ext in AUDIO_EXT or (mime or "").startswith("audio/"):
        return transcribe.transcribe_file(path) or ""
    if ext in VIDEO_EXT or (mime or "").startswith("video/"):
        from context.video import extract_audio
        audio_path = extract_audio(path)
        try:
            return transcribe.transcribe_file(audio_path) or ""
        finally:
            try:
                os.remove(audio_path)
            except OSError:
                pass
    if ext in IMAGE_EXT or (mime or "").startswith("image/"):
        return _extract_image_sync(path, mime)
    with open(path, "rb") as f:
        raw = f.read()
    return doc_extract.extract_text(raw, mime=mime, filename=filename, max_chars=300_000)


def _extract_image_sync(path: str, mime: str) -> str:
    with open(path, "rb") as f:
        raw = f.read()
    mime = mime or mimetypes.guess_type(path)[0] or "image/jpeg"

    async def _run():
        from llm import vision
        return await vision.describe_image(raw, mime=mime)

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, _run()).result()
        return loop.run_until_complete(_run())
    except RuntimeError:
        return asyncio.run(_run())


def _embed_chunks(asset: dict, space: dict, text: str) -> int:
    chunks = _chunk(text)
    if not chunks:
        return 0
    col = vector_store.get_collection("documents")
    asset_id = str(asset["id"])
    try:
        col.delete(where={"asset_id": asset_id})
    except Exception:
        pass
    title = asset.get("title") or asset.get("url") or f"asset-{asset_id}"
    for i, ch in enumerate(chunks):
        vector_store.add(
            "documents",
            ch,
            metadata={
                "space_id": str(space["id"]),
                "space_name": space["name"],
                "asset_id": asset_id,
                "kind": asset.get("kind", "file"),
                "source": title,
                "chunk": i,
            },
        )
    return len(chunks)


def ingest_asset(asset_id: int) -> dict:
    """Synchronous ingest — extract text, chunk, embed. Updates asset status."""
    asset = context_store.get_asset(asset_id)
    if not asset:
        return {"error": f"Asset {asset_id} not found"}
    space = context_store.get_space(asset["space_id"])
    if not space:
        return {"error": "Space not found"}

    context_store.update_asset(asset_id, status="processing", error="")
    try:
        kind = asset["kind"]
        text = ""

        if kind == "note":
            text = asset.get("extracted_text") or ""
        elif kind == "link":
            url = asset.get("url") or ""
            scraped = scrape_url(url, max_chars=50_000)
            if scraped.get("error"):
                raise RuntimeError(scraped["error"])
            title = scraped.get("title") or url
            text = f"Title: {title}\nURL: {url}\n\n{scraped.get('text', '')}"
            context_store.update_asset(asset_id, title=title)
        elif asset.get("source_path") and os.path.isfile(asset["source_path"]):
            text = _extract_from_file(
                asset["source_path"],
                asset.get("mime") or "",
                os.path.basename(asset["source_path"]),
            )
        else:
            text = asset.get("extracted_text") or ""

        text = (text or "").strip()
        if not text:
            raise RuntimeError("No extractable text from this asset")

        chunk_count = _embed_chunks(asset, space, text)
        context_store.update_asset(
            asset_id,
            status="ready",
            extracted_text=text[:100_000],
            text_chars=len(text),
            chunk_count=chunk_count,
            error="",
        )
        return {"asset_id": asset_id, "status": "ready", "chunks": chunk_count, "chars": len(text)}
    except Exception as e:
        logger.error(f"[context/ingest] asset {asset_id} failed: {e}")
        context_store.update_asset(asset_id, status="failed", error=str(e)[:500])
        return {"asset_id": asset_id, "status": "failed", "error": str(e)}


def ingest_asset_async(asset_id: int):
    """Run ingest in a background thread."""
    def _run():
        ingest_asset(asset_id)

    t = threading.Thread(target=_run, daemon=True, name=f"ingest-{asset_id}")
    t.start()
    return t


def delete_asset_vectors(asset_id: int):
    try:
        col = vector_store.get_collection("documents")
        col.delete(where={"asset_id": str(asset_id)})
    except Exception as e:
        logger.debug(f"[context/ingest] vector delete failed for {asset_id}: {e}")
