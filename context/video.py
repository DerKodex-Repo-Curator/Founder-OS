"""Extract audio from video files via ffmpeg (system dependency)."""
import logging
import os
import shutil
import subprocess
import tempfile

logger = logging.getLogger(__name__)


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def extract_audio(video_path: str) -> str:
    """Extract audio track from video to a temp .wav file. Returns path or raises."""
    if not ffmpeg_available():
        raise RuntimeError(
            "ffmpeg is not installed. Install ffmpeg to transcribe video files."
        )
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")

    fd, out_path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    try:
        proc = subprocess.run(
            [
                "ffmpeg", "-y", "-i", video_path,
                "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
                out_path,
            ],
            capture_output=True,
            text=True,
            timeout=600,
        )
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "ffmpeg failed")[:500]
            raise RuntimeError(err)
        if not os.path.isfile(out_path) or os.path.getsize(out_path) == 0:
            raise RuntimeError("ffmpeg produced an empty audio file")
        return out_path
    except Exception:
        if os.path.isfile(out_path):
            try:
                os.remove(out_path)
            except OSError:
                pass
        raise
