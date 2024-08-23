#
# SWEEPER
#
from pathlib import Path
import subprocess as sp
import os
import tempfile
import shutil

PVIDEOS = Path(os.environ.get("VIDEOS", "./videos"))
PPILE = Path(os.environ.get("PILE", "./videos/pile"))
PTMP = Path(os.environ.get("TMP", "./tmp"))
PMP3 = Path(os.environ.get("MP3", "./mp3"))
PCACHE = Path(os.environ.get("CACHE", "./cache"))

CACHE_NAMES = set(p.name for p in PCACHE.glob("*"))
INPUT_EXT = {".mkv", ".webm", ".mp4"}
VIDEO_RECODE_EXT = {".mkv", ".webm"}
AUDIO_EXTRACT_EXT = {".mp4"}
PREVIEW_EXT = {".mp4"}

import logging

L = logging.getLogger(__name__)

def pcall(cmd):
    L.debug(f"Running {cmd}")
    p = sp.run(cmd, capture_output=True, check=False)
    if p.returncode != 0:
        L.error(f"Failed running {cmd}")
        L.error(p.stderr)
        L.error(p.stdout)
        return False
    return True

def list_videos():
    return [
        p
        for p in PVIDEOS.glob("**/*")
        if (p.suffix in INPUT_EXT) and (not p.name.startswith("."))
    ]


def generate_preview(path_src):
    preview_name = Path(path_src).name + ".png"
    if preview_name in CACHE_NAMES:
        return
    if not Path(path_src).suffix in PREVIEW_EXT:
        return
    L.info(f"Generate preview {path_src}")
    path_dst = PCACHE / preview_name
    pcall(
        [
            "ffmpeg",
            "-n",
            "-v",
            "debug",
            "-i",
            str(path_src),
            "-ss",
            "00:00:20.000",
            "-vframes",
            "1",
            str(path_dst),
        ]
    )
    if not path_dst.exists():
        L.error(f"Second try for {path_src}. Using first frame.")
        pcall(
            [
                "ffmpeg",
                "-n",
                "-v",
                "fatal",
                "-i",
                str(path_src),
                "-ss",
                "00:00:00.000",
                "-vframes",
                "1",
                str(path_dst),
            ]
        )
    if not path_dst.exists():
        L.error(
            f"Could not create preview image for {path_src}. Leaving empty file as sentinel."
        )
        # TODO Replace by dummpy image
        path_dst.touch()


def extract_audio(path_src):
    path_dst = PMP3 / (path_src.name + ".mp3")
    if path_dst.exists():
        return
    # only extract audio from mp4 files, so that we don't run into race conditions
    if not Path(path_src).suffix in AUDIO_EXTRACT_EXT:
        return

    L.info(f"Extract audio {path_src}")
    with tempfile.TemporaryDirectory(dir=PTMP) as tmpdir:
        path_tmp: Path = Path(tmpdir) / "tmp.mp3"
        pcall(
            [
                "ffmpeg",
                "-i",
                str(path_src),
                str(path_tmp),
            ]
        )
        assert path_tmp.exists()
        shutil.move(path_tmp, path_dst)
    assert path_dst.exists()


def recode(path_src):
    if not Path(path_src).suffix in VIDEO_RECODE_EXT:
        return

    L.info(f"Recode {path_src}")
    path_dst = Path(str(path_src) + ".mp4")
    if not path_dst.exists():
        with tempfile.TemporaryDirectory(dir=PTMP) as tmpdir:
            path_tmp: Path = Path(tmpdir) / "tmp.mp4"
            pcall(
                [
                    "ffmpeg",
                    "-v",
                    "fatal",
                    "-n",
                    "-i",
                    str(path_src),
                    "-c:a",
                    "aac",
                    str(path_tmp),
                ]
            )
            assert path_tmp.exists()
            shutil.move(path_tmp, path_dst)
    assert path_dst.exists()
    path_src.unlink()
    generate_preview(path_dst)

def sweep():
    L.info("Sweep start")
    global CACHE_NAMES
    CACHE_NAMES = set(p.name for p in PCACHE.glob("*"))
    for vpath in list_videos():
        try:
            generate_preview(vpath)
        except Exception as e:
            L.error(e)
        try:
            recode(vpath)
        except Exception as e:
            L.error(e)
        try:
            extract_audio(vpath)
        except Exception as e:
            L.error(e)
    L.info("Sweep done.")
