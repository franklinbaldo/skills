#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["cyclopts>=3,<5", "yt-dlp[default]>=2026.10.26", "static-ffmpeg==3.0"]
# ///
"""Download a YouTube playlist as MP3 files with metadata and resumable progress."""

from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import ExitStack
from pathlib import Path
from shutil import which
from urllib.parse import parse_qs, urlsplit

from cyclopts import App
from static_ffmpeg.run import get_or_fetch_platform_executables_else_raise
from yt_dlp import YoutubeDL
from yt_dlp.postprocessor import FFmpegExtractAudioPP, FFmpegMetadataPP, PostProcessor
from yt_dlp.utils import DownloadError, PostProcessingError

app = App(help=__doc__)


def ensure_ffmpeg() -> str | None:
    """Reuse system tools or fetch a private pair without changing global PATH."""
    if all(which(tool) for tool in ("ffmpeg", "ffprobe")):
        return None
    app.console.print("Preparing private FFmpeg and ffprobe (downloaded on first use)...")
    try:
        ffmpeg, ffprobe = get_or_fetch_platform_executables_else_raise()
        if not Path(ffmpeg).is_file() or not Path(ffprobe).is_file():
            raise OSError("FFmpeg provider did not produce both executables")
        return str(Path(ffmpeg).parent)
    except Exception as error:
        app.console.print(f"Could not prepare FFmpeg: {error}", markup=False)
        raise RuntimeError(f"Could not prepare FFmpeg: {error}") from error


class DeferredAudioPP(PostProcessor):
    """Wait for tools only after media arrives, then use yt-dlp's processors."""

    def __init__(self, downloader: YoutubeDL, ready: Future):
        super().__init__(downloader)
        self.ready = ready

    def run(self, info):
        try:
            location = self.ready.result()
        except Exception as error:
            raise PostProcessingError(f"FFmpeg unavailable; source audio retained: {error}") from error
        if location is not None:
            self._downloader.params["ffmpeg_location"] = location
        audio = FFmpegExtractAudioPP(self._downloader, preferredcodec="mp3", preferredquality="0")
        metadata = FFmpegMetadataPP(self._downloader, add_metadata=True)
        deleted_audio, info = audio.run(info)
        deleted_metadata, info = metadata.run(info)
        return deleted_audio + deleted_metadata, info


@app.default
def main(
    url: str,
    *,
    destination: Path = Path("mp3"),
    cookies: Path | None = None,
    list_only: bool = False,
) -> None:
    """Download audio, or list playlist entries without downloading.

    Parameters
    ----------
    url
        HTTPS YouTube URL containing a list parameter.
    destination
        Output folder; relative paths resolve against the working directory.
    cookies
        Optional local Netscape-format cookies file for authenticated access.
    list_only
        Print entries without downloading; does not require FFmpeg.
    """
    try:
        parsed = urlsplit(url)
        valid = (
            parsed.scheme == "https"
            and parsed.hostname in {"youtube.com", "www.youtube.com", "music.youtube.com", "youtu.be"}
            and not parsed.username
            and not parsed.password
            and parsed.port in {None, 443}
            and bool(parse_qs(parsed.query).get("list"))
        )
    except ValueError:
        valid = False
    if not valid:
        app.console.print("Provide an HTTPS YouTube playlist URL containing list=ID.")
        raise SystemExit(2)
    if cookies is not None and not cookies.is_file():
        app.console.print("Cookies file does not exist or is not a regular file.")
        raise SystemExit(2)

    options = {
        "noplaylist": False,
        "windowsfilenames": True,
        # Continue past unavailable entries, but retain a nonzero failure status.
        "ignoreerrors": "only_download",
    }
    if which("node"):
        options["js_runtimes"] = {"node": {}}
    if cookies is not None:
        options["cookiefile"] = str(cookies.resolve())
    if list_only:
        options.update(
            extract_flat="in_playlist",
            skip_download=True,
            forceprint={"video": ["%(playlist_index)s - %(title)s [%(id)s]"]},
        )
    else:
        destination = destination.resolve()
        destination.mkdir(parents=True, exist_ok=True)
        options.update(
            format="bestaudio/best",
            continuedl=True,
            overwrites=False,
            download_archive=str(destination / "downloaded.txt"),
            paths={"home": str(destination)},
            outtmpl={
                "default": "%(playlist_title).80s [%(playlist_id)s]/"
                "%(playlist_index)03d - %(title).120s [%(id)s].%(ext)s"
            },
        )
    try:
        with ExitStack() as stack:
            downloader = stack.enter_context(YoutubeDL(options))
            if not list_only:
                executor = stack.enter_context(ThreadPoolExecutor(max_workers=1))
                ready = executor.submit(ensure_ffmpeg)
                downloader.add_post_processor(DeferredAudioPP(downloader, ready))
            status = downloader.download([url])
    except (DownloadError, OSError) as error:
        app.console.print(str(error), markup=False)
        raise SystemExit(1) from error
    if status:
        app.console.print("Some entries failed. Completed files are preserved; rerun to retry.")
        raise SystemExit(1)
    if not list_only:
        app.console.print(f"Finished: {destination}", markup=False)


if __name__ == "__main__":
    app()
