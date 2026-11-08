---
name: youtube-playlist-mp3
description: Download a YouTube or YouTube Music playlist as individual MP3 files using yt-dlp and FFmpeg, with metadata, resumable downloads and a completion archive. Use when the user asks to save playlist audio, convert a playlist to MP3, or resume an earlier playlist download. Runs through uv with PEP 723 dependencies on Windows, macOS and Linux.
---

# YouTube playlist to MP3

Use the bundled script instead of implementing YouTube extraction yourself.
Resolve `scripts/download_playlist.py` relative to this skill's directory; resolve
the output folder relative to the user's working directory.

## Workflow

1. Obtain the playlist URL and use the requested output folder, or `./mp3`.

2. Check `uv` on PATH. If missing, suggest installation; on Windows:
   `winget install --id astral-sh.uv --exact`. PEP 723 declares `static-ffmpeg`
   alongside the Python dependencies. The script reuses FFmpeg and ffprobe when
   both are installed; otherwise the provider downloads a private pair on first
   use and caches it within its package in uv's environment. No administrator
   access, system installation or persistent PATH change is needed. The first
   conversion requires network access for that binary download. `--help` and
   `--list-only` do not fetch FFmpeg binaries. Unsupported platforms or download
   failures are reported at conversion time; downloaded source audio is retained.
   Media downloading and binary preparation run concurrently. Only conversion
   waits for FFmpeg, so a first-use binary download does not delay media extraction.

3. Use a supported JavaScript runtime for YouTube challenges. The script enables
   Node when found; otherwise yt-dlp can use its default Deno runtime. If extraction
   reports a missing or outdated runtime, consult the official yt-dlp documentation
   and resolve that specific dependency before retrying.

4. Run the download with the URL quoted. No manual virtualenv or pip is needed:

   ```sh
   uv run /path/to/skill/scripts/download_playlist.py "https://www.youtube.com/playlist?list=ID" --destination ./mp3
   ```

   To inspect entries without downloading (FFmpeg is not needed):

   ```sh
   uv run /path/to/skill/scripts/download_playlist.py "https://www.youtube.com/playlist?list=ID" --list-only
   ```

5. For an authenticated playlist, use `--cookies /private/path/cookies.txt` only
   with the user's authorized session. The file must use Netscape format. Keep
   cookies outside repositories; never print or publish them. Browser cookie
   decryption is not handled by this skill. Do not bypass access restrictions.

6. Verify the exit status and actual MP3 output. Report failures and unavailable
   entries separately. When practical, probe a produced file with `ffprobe` and
   check playback; command success alone does not prove audio quality.

## Behavior and recovery

- Best available audio is converted to MP3 VBR quality 0 with metadata. Conversion
  cannot improve source quality. Files are grouped by playlist title and ID.
- Names include playlist position and video ID and are compatible with Windows.
- Rerun the same command after interruption. Partial downloads can resume;
  completed video IDs are stored in `downloaded.txt` after postprocessing.
- The archive is shared by downloads to the same destination. A video already
  archived there is skipped even in a different playlist. Use a separate destination
  for independent playlist copies. Do not remove the archive without explaining
  the duplicate-download consequences; it also skips files manually deleted later.
- Unavailable entries do not stop later entries. A failure produces a nonzero
  status; preserve completed files and diagnose before retrying.
- Exit codes: 0 completed, 1 download/postprocessing failure (including FFmpeg
  provisioning), 2 invalid input. A conversion failure must not archive an item
  as completed or delete its downloaded source. Rerun after resolving the failure.
- Do not claim live downloading was tested if only help, listing or mocks ran.

Sources: [yt-dlp](https://github.com/yt-dlp/yt-dlp),
[static-ffmpeg](https://github.com/zackees/static_ffmpeg),
[uv scripts and PEP 723](https://docs.astral.sh/uv/guides/scripts/).

## Real-use postmortem

After material use, assess routing, outcome, quality delta, concrete instruction
effect, and any friction/workaround. Routine success stays ephemeral. If there is
actionable learning, search `franklinbaldo/skills` issues and update a matching issue
or open a sanitized **Skill use feedback** issue. Never publish secrets or
private/confidential data merely to report feedback.
