#
# # Open Ends
#
# ## Features
# - Show duration in gallery
#
#
# ## Nice to Have
# - Better logging in Web console
#   - Forward all logs to websocket
# - Convert "Download" tab into "Logging Console"
#   - Take https:// entries to search as download requests
#

from datetime import date, datetime
from pathlib import Path
from queue import Queue
from socket import error
from threading import Thread
import os
import flask
import flask_socketio as flaskio
import json
import logging
import re
import subprocess
import shutil
import click
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
import subprocess

logging.basicConfig(format="%(asctime)s logger=%(name)s lvl=%(levelname)s pid=%(process)d %(message)s")
L = logging.getLogger(__name__)
L.setLevel(logging.INFO)

def validate(env_var, default_path, create=False):
    path = Path(os.environ.get(env_var, default_path))
    L.debug(f"{env_var}={path}")
    if not path.is_dir():
        if create:
            # mkdir
            path.mkdir(parents=True, exist_ok=True)
            L.info(f"Created {env_var}: {path}")
        else:
            L.error(f"{env_var} does not exist: {path}")
    return path

PVIDEOS = validate("VIDEOS", "./videos")
PPILE= validate("PILE", "./videos/pile")
PTRASH = validate("PTRASH", PVIDEOS / "trash/", create=True)
PMP3= validate("MP3", "./mp3")
PCACHE= validate("CACHE", "./cache")
PTMP= validate("TMP", "./tmp")
PDB = PCACHE / "pile.db"
DEBUG = os.environ.get("DEBUG", False)

if DEBUG:
    L.setLevel(logging.DEBUG)
    L.debug("DEBUG=true")


#
# Thread Pool Management
#

def pcall(cmd):
    cmd_txt = " ".join(cmd)
    L.debug(f"Running {cmd_txt}")
    p = subprocess.run(cmd, capture_output=True, check=False)
    if p.returncode != 0:
        L.error(f"Failed running {cmd_txt}")
        L.error(p.stderr)
        L.error(p.stdout)
        return False
    return p

class CallErrror(Exception):
    pass

def call_sync(argv):
    cmd_line = " ".join(argv)
    cmd = argv[0]
    L.debug(f"Running `{cmd_line}`")
    with subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as proc:
        # stderr is redirected stdout, so we see all messages here
        for line in proc.stdout:
            L.debug(f"{cmd} > " + line.decode("utf-8").rstrip("\n"))
        code = proc.wait()
        if code == 0:
            L.info(f"{cmd} > Done running `{cmd_line}`.")
        else:
            L.error(f"{cmd} > Failed running `{cmd_line}` with code {code}.")
            raise CallErrror(f"Failed running `{cmd_line}` with code {code}.")

executor = ThreadPoolExecutor(max_workers=4)
def exec_submit(fn, *args, **kwargs):
    future = executor.submit(fn, *args, **kwargs)
    def done_callback(future):
        if future.exception():
            L.error(f"Error in {fn.__name__}: {future.exception()}")
        else:
            L.debug(f"Done {fn.__name__}")
    future.add_done_callback(done_callback)
    return future


#
# File Actions
#
# Those functions directly abstract shell commands we are running (usually against files)
# They are all prefixed with "generate_"
#
def generate_poster(path_src, path_dst):
    pcall([ "ffmpeg", "-n", "-v", "debug", "-i", str(path_src), "-ss", "00:00:20.000", "-vframes", "1", str(path_dst) ])
    if path_dst.exists():
        return True
    L.error(f"Second try for {path_src}. Using first frame.")
    pcall([ "ffmpeg", "-n", "-v", "fatal", "-i", str(path_src), "-ss", "00:00:00.000", "-vframes", "1", str(path_dst) ])
    if path_dst.exists():
        return True
    return False

def generate_duration(path):
    p = pcall([ "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path) ])
    if p:
        return float(p.stdout)
    return None

def generate_audio(path_src, path_dst):
    L.debug(f"Extract audio {path_src}")
    with tempfile.TemporaryDirectory(dir=PTMP) as tmpdir:
        path_tmp: Path = Path(tmpdir) / "tmp.mp3"
        pcall([ "ffmpeg", "-i", str(path_src), str(path_tmp), ])
        assert path_tmp.exists()
        shutil.move(path_tmp, path_dst)
    return path_dst.exists()

def generate_recode(path_src, path_dst):
    L.info(f"Recode {path_src} -> {path_dst}")
    with tempfile.TemporaryDirectory(dir=PTMP) as tmpdir:
        path_tmp: Path = Path(tmpdir) / "tmp.mp4"
        pcall([ "ffmpeg", "-v", "fatal", "-n", "-i", str(path_src), "-c:a", "aac", str(path_tmp), ])
        assert path_tmp.exists()
        shutil.move(path_tmp, path_dst)
    assert path_dst.exists()
    path_src.unlink() # rm source

def generate_download(url, output_dir):
    today = date.today().isoformat()
    L.info(f"Download {url}")
    call_sync([
        "yt-dlp",
        "--no-progress",
        "--restrict-filenames",
        "--format",
        "bestvideo[height<=760]+bestaudio",
        "-o",
        f"{output_dir}/{today} %(title)s via %(uploader)s.%(ext)s",
        url,
    ])

def generate_keep_ytdl_updated():
    while True:
        pcall(["pip", "install", "-U", "yt-dlp"])
        if p := pcall(["yt-dlp", "--version"]):
            L.info(f"Updated yt-dlp to {p.stdout.decode('utf-8').strip()}")
        L.info("Updated yt-dlp.")
        time.sleep(60 * 60 * 12)


#
# Meta Database
#
import sqlite3
import threading
def db_connection():
    thread_local = threading.local()
    if not hasattr(thread_local, 'sqlite_db'):
        thread_local.sqlite_db = sqlite3.connect(PDB)
    return thread_local.sqlite_db

def db_init():
    db = db_connection()
    db.execute("""
        CREATE TABLE IF NOT EXISTS video (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE,
            title TEXT,
            duration_sec INTEGER,
            video_url TEXT,
            poster_url TEXT,
            audio_path TEXT
        );
    """)
    db.commit()

def db_scan_videos(root: Path):
    _re_date = re.compile("(\d\d\d\d\-\d\d-\d\d).*")
    VIDEO_EXT = {".mp4"}
    cnt = 0
    db = db_connection()
    for path in root.glob("**/*"):
        date = _re_date.match(path.name)
        title = path.name
        video_url = "/video/" + "/".join(path.parts[1:])
        if (path.suffix in VIDEO_EXT) and (not path.name.startswith(".")):
            db.execute("INSERT OR IGNORE INTO video (path, video_url, title) VALUES (?, ?, ?)", (str(path), video_url, title))
            cnt += 1
    db.commit()
    L.info(f"Found {cnt} videos.")

def set_duration(path: Path):
    duration = generate_duration(path)
    if duration:
        db = db_connection()
        db.execute("UPDATE video SET duration_sec = ? WHERE path = ?", (duration, str(path)))
        db.commit()
        L.debug(f"Set duration for {path} to {duration} seconds.")
        return True
    else:
        L.error(f"Failed to get duration for {path}")
    return False

def db_scan_duration():
    db = db_connection()
    res = db.execute("SELECT path FROM video WHERE duration_sec IS NULL")
    cnt = 0
    for row in res:
        path = Path(row[0])
        exec_submit(set_duration, path)
        cnt += 1
    L.info(f"Queued {cnt} duration computations.")

def set_poster(path: Path):
    L.debug(f"Generate poster {path}.")
    poster_path = PCACHE / (path.name + ".png")
    if generate_poster(path, poster_path):
        poster_url = "/poster/" + path.name + ".png"
        db = db_connection()
        db.execute("UPDATE video SET poster_url = ? WHERE path = ?", (poster_url, str(path)))
        db.commit()
        L.debug(f"Set poster for {path} to {poster_url}.")
    else:
        L.error(f"Failed to generate poster for {path}.")

def db_scan_poster(root: Path):
    db = db_connection()
    res = db.execute("SELECT path FROM video WHERE poster_url IS NULL")
    cnt_found = 0
    cnt_queued = 0
    for row in res:
        path = Path(row[0])
        poster_path = root / (path.name + ".png")
        if poster_path.exists():
            cnt_found += 1
            poster_url = "/poster/" + path.name + ".png"
            db.execute("UPDATE video SET poster_url = ? WHERE path = ?", (poster_url, str(path)))
        else:
            cnt_queued += 1
            exec_submit(set_poster, path)
    db.commit()
    L.info(f"Found {cnt_found} posters. Queued {cnt_queued} poster generations.")

def db_clear_posters():
    db = db_connection()
    db.execute("UPDATE video SET poster_url = NULL")
    db.commit()

def db_clear_audio():
    db = db_connection()
    db.execute("UPDATE video SET audio_path = NULL")
    db.commit()

def db_set_audio(path: Path, audio_path: Path):
    db = db_connection()
    db.execute("UPDATE video SET audio_path = ? WHERE path = ?", (str(audio_path), str(path)))
    db.commit()

def db_scan_audio(root):
    AUDIO_EXTRACT_EXT = {".mp4"}
    db = db_connection()
    res = db.execute("SELECT path FROM video WHERE audio_path IS NULL")
    cnt_found = 0
    cnt_queued = 0
    for row in res:
        path = Path(row[0])
        audio_path = root / (path.name + ".mp3")
        if audio_path.exists():
            db.execute("UPDATE video SET audio_path = ? WHERE path = ?", (str(audio_path), str(path)))
            cnt_found += 1
        elif path.suffix in AUDIO_EXTRACT_EXT:
            cnt_queued += 1
            exec_submit(generate_audio, path, audio_path)
        else:
            L.debug(f"Audio extraction skipped for {path}")
    db.commit()
    L.info(f"Found {cnt_found} audio files. Queued {cnt_queued} audio extractions.")

def db_scan_recode(root: Path):
    VIDEO_RECODE_EXT = {".webm", ".mkv"}
    cnt = 0
    for path in root.glob("**/*"):
        if not path.suffix in VIDEO_RECODE_EXT:
            continue
        recode_path = root / (path.name + ".mp4")
        if recode_path.exists():
            continue
        exec_submit(generate_recode, path, recode_path)
        cnt += 1
    L.info(f"Queued {cnt} videos for recoding.")

    
#
# Flask App
#
app = flask.Flask(__name__, static_folder="./static", template_folder="./template")

socketio = flaskio.SocketIO(app, cors_allowed_origins="*")

def websocket_send(msg):
    "Sends message to all known web-sockets"
    # L.debug(f"socket > {msg}")
    socketio.emit("message", msg, broadcast=True)

class SocketLogHandler(logging.Handler):
    def emit(self, record):
        websocket_send(self.format(record))

socket_formatter = logging.Formatter("%(asctime)s %(message)s", datefmt="%H:%M:%S")
socket_log_handler = SocketLogHandler()
socket_log_handler.setFormatter(socket_formatter)
L.addHandler(socket_log_handler)

@app.route("/download")
def serve_download():
    return flask.render_template("download.tpl")


@app.route("/video/<path:filepath>")
def serve_video(filepath):
    base_path = PVIDEOS.resolve
    return flask.send_from_directory(PVIDEOS , filepath)


@app.route("/poster/<path:filepath>")
def serve_poster(filepath):
    return flask.send_from_directory(PCACHE, filepath)


@app.route("/static/<path:filepath>")
def serve_static(filepath):
    return static_file(filepath, root="./static")


@app.route("/")
@app.route("/gallery")
def serve_gallery():
    _re_date = re.compile("(\d\d\d\d\-\d\d-\d\d).*")
    VIDEO_EXT = {".mkv", ".webm", ".mp4"}
    paths = [
        (p, _re_date.match(p.name))
        for p in PVIDEOS.glob("**/*")
        if (p.suffix in VIDEO_EXT) and (not p.name.startswith("."))
    ]
    L.debug(f"Found {len(paths)} videos.")

    def key(o):
        p, m = o
        if m:
            return "y" + p.name
        else:
            return "x"

    paths = sorted(paths, reverse=True, key=key)
    def path_to_video(path):
        return "/video/" + "/".join(path.relative_to(PVIDEOS).parts)
    def path_to_poster(path):
        return "/poster/" + path.name + ".png"

    videos = [
        {
            "name": o[0].name,
            "src": path_to_video(o[0]),
            "poster": path_to_poster(o[0])
        }
        for o in paths
    ]
    return flask.render_template("gallery.tpl", videos=videos)


@app.route("/delete", methods=["POST"])
def video_del():
    payload = flask.request.get_json()
    src = Path(payload["src"]).relative_to("/video/")
    dst = PTRASH / (src.name + ".del")
    assert (PVIDEOS / src).exists()
    shutil.move(PVIDEOS / src, dst)
    L.info(f"Moved to trash: {src} -> {dst}")
    return {"status": "OK"}

@app.route("/download/q", methods=["POST"])
def q_put():
    payload = flask.request.get_json()
    url = payload.get("url")
    future = exec_submit(generate_download, url, PPILE)
    def cb(future):
        future.result() # re-raise exception
        db_scan_recode(PVIDEOS)
        db_scan_poster(PCACHE)
    future.add_done_callback(cb)
    return flask.jsonify({"success": True, "msg": f"Queued download {url}"})

@socketio.on("connect")
def test():
    L.debug("Socket connected")
    socketio.send(f"Welcome!\n")

@socketio.on("message")
def handle_message(msg):
    L.debug(f"Socket received: {msg}")

@click.command()
@click.option("-p", "--port", default=8083, help="Port to listen on", envvar="PORT")
def main(port):
    db_init()

    # Re-scan for poster & audio files on startup
    db_clear_posters()
    db_clear_audio()

    db_scan_videos(PVIDEOS)
    db_scan_duration()
    db_scan_poster(PCACHE)
    db_scan_audio(PMP3)
    db_scan_recode(PVIDEOS)

    # This will permanently consume one thread from the pool
    exec_submit(generate_keep_ytdl_updated)

    # app.jinja_env.auto_reload = True
    # app.config["TEMPLATES_AUTO_RELOAD"] = True
    # suppress werkzeug logging. For some reason we have to do this late in the process.
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    socketio.run(app, host="0.0.0.0", port=port, debug=DEBUG) # BLOCK

    # CTRL-C will get us here.
    # Cleanup
    executor.shutdown()

if __name__ == "__main__":
    main()
