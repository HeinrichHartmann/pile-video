#
# SWEEPER
#
from pathlib import Path
import subprocess as sp
import tempfile
import shutil

PVIDEOS = Path("./videos")
PCACHE = Path("./cache")
PTMP = Path("./tmp")
CACHE_NAMES = set(p.name for p in PCACHE.glob("*"))

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
    VIDEO_EXT = {".mkv", ".webm", ".mp4"}
    return [
        p
        for p in PVIDEOS.glob("**/*")
        if (p.suffix in VIDEO_EXT) and (not p.name.startswith("."))
    ]


def have_preview(path):
    preview_name = Path(path).name + ".png"
    return preview_name in CACHE_NAMES


def generate_preview(path_src):
    L.info(f"!Generate preview {path_src}")
    path_dst = PCACHE / (Path(path_src).name + ".png")
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
        path_dst.touch()


_RECODE_EXT = {".mkv"}


def needs_recode(path):
    return Path(path).suffix in _RECODE_EXT


def recode(path_src):
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
    # rename for future deletion
    path_src.rename(str(path_src) + ".bak")


def sweep():
    L.info("Sweep start.")
    global CACHE_NAMES
    CACHE_NAMES = set(p.name for p in PCACHE.glob("*"))
    for vpath in list_videos():
        if not have_preview(vpath):
            try:
                generate_preview(vpath)
            except Exception as e:
                L.error(e)
        if needs_recode(vpath):
            try:
                recode(vpath)
            except Exception as e:
                L.error(e)
    L.info("Sweep done.")
