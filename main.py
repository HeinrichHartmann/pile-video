#
# # Open Ends
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

from concurrent.futures import Future

def all_done_callback(futures, callback):
    """
    Attaches a callback to a list of futures that will execute the
    callback function once all futures have completed.

    Args:
        futures (list): A list of Future objects.
        callback (function): The function to call once all futures are done.
    """
    total_futures = len(futures)
    completed_futures = [0]  # Use a list for mutability
    def future_callback(fut: Future):
        nonlocal completed_futures
        completed_futures[0] += 1
        if completed_futures[0] == total_futures:
            callback()
    for f in futures:
        f.add_done_callback(future_callback)


#
# Thread Pool Management
#

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

def call_capture(argv):
    cmd_line = " ".join(argv)
    cmd = argv[0]
    L.debug(f"Running `{cmd_line}`")
    try:
        completed_process = subprocess.run(argv, capture_output=True, check=True)
    except subprocess.CalledProcessError as e:
        L.error(f"{cmd} > Failed running `{cmd_line}` with code {e.returncode}.")
        L.error(f"{cmd} STDOUT > {e.stdout.decode('utf-8')}")
        L.error(f"{cmd} STDERR > {e.stderr.decode('utf-8')}")
        raise e
    return completed_process.stdout.decode("utf-8")

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
    try:
        call_sync([ "ffmpeg", "-n", "-v", "error", "-i", str(path_src), "-ss", "00:00:20.000", "-vframes", "1", str(path_dst) ])
        assert path_dst.exists()
    except:
        L.error(f"Second try for {path_src}. Using first frame.")
        call_sync([ "ffmpeg", "-n", "-v", "fatal", "-i", str(path_src), "-ss", "00:00:00.000", "-vframes", "1", str(path_dst) ])
    assert path_dst.exists()

def generate_duration(path):
    return float(
        call_capture([ "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path) ])
    )

def generate_audio(path_src, path_dst):
    L.debug(f"Extract audio {path_src}")
    with tempfile.TemporaryDirectory(dir=PTMP) as tmpdir:
        path_tmp: Path = Path(tmpdir) / "tmp.mp3"
        call_sync([ "ffmpeg", "-i", str(path_src), str(path_tmp), ])
        assert path_tmp.exists()
        shutil.move(path_tmp, path_dst)
    return path_dst.exists()

def generate_recode(path_src, path_dst):
    L.info(f"Recode {path_src} -> {path_dst}")
    with tempfile.TemporaryDirectory(dir=PTMP) as tmpdir:
        path_tmp: Path = Path(tmpdir) / "tmp.mp4"
        call_sync([ "ffmpeg", "-v", "fatal", "-n", "-i", str(path_src), "-c:a", "aac", str(path_tmp), ])
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
        try:
            call_sync(["pip", "install", "-U", "yt-dlp"])
            version = call_capture(["yt-dlp", "--version"])
            L.info(f"Updated yt-dlp to {version}")
            L.info("Updated yt-dlp.")
        except Exception as e:
            L.error(f"Update yt-dlp failed: {e}")
        time.sleep(60 * 60 * 12)

#
# Video Data Class
#
class Video:
    def __init__(self, video_dict):
        self.path = Path(video_dict["path"])
        self.title = video_dict["title"]
        self.date = video_dict["date"]
        self.duration_sec = video_dict["duration_sec"]
        self.video_url = video_dict["video_url"]
        self.poster_url = video_dict["poster_url"]

    def title_str(self):
        name = Path(self.path).name
        # remove 1-3 letter suffixes .xxx
        while m := re.match(r"(.*)\.\w{1,4}$", name):
            name = m.group(1)
        return name

#
# Meta Database
#
import sqlite3
import threading
def db_connection():
    thread_local = threading.local()
    if not hasattr(thread_local, 'sqlite_db'):
        thread_local.sqlite_db = sqlite3.connect(PDB)
        thread_local.sqlite_db.row_factory = sqlite3.Row
    return thread_local.sqlite_db

def db_init():
    db = db_connection()
    db.execute("""
        CREATE TABLE IF NOT EXISTS video (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE,
            date TIMESTAMP,
            title TEXT,
            duration_sec INTEGER,
            video_url TEXT,
            poster_url TEXT,
            audio_path TEXT
        );
    """)
    db.commit()

def db_iter_videos():
    db = db_connection()
    res = db.execute("SELECT path, title, duration_sec, video_url, poster_url, date FROM video ORDER BY date DESC")
    for row in res:
        yield Video(dict(row))


_re_date = re.compile("(\d\d\d\d\-\d\d-\d\d).*")
def db_scan_videos(root: Path, prefix=""):
    VIDEO_EXT = {".mp4"}
    cnt = 0
    db = db_connection()
    for path in root.glob("**/*"):
        if path.name.startswith("."):
            continue
        if not path.suffix in VIDEO_EXT:
            continue
        if not path.name.startswith(prefix):
            continue

        title = path.name
        video_url = "/video/" + "/".join(path.relative_to(root).parts)
        date = None
        if m := _re_date.match(path.name):
            date = m.group(1)
            title = path.name[len(date) + 1:]
        db.execute("INSERT OR IGNORE INTO video (path, video_url, title, date) VALUES (?, ?, ?, ?)", (str(path), video_url, title, date))
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

def db_scan_duration(prefix=""):
    db = db_connection()
    res = db.execute("SELECT path FROM video WHERE duration_sec IS NULL")
    cnt = 0
    for row in res:
        path = Path(row[0])
        if not path.name.startswith(prefix):
            continue
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

def db_scan_poster(root: Path, prefix=""):
    db = db_connection()
    res = db.execute("SELECT path FROM video WHERE poster_url IS NULL")
    cnt_found = 0
    cnt_queued = 0
    for row in res:
        path = Path(row[0])
        if not path.name.startswith(prefix):
            continue
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

def db_scan_audio(root, prefix=""):
    AUDIO_EXTRACT_EXT = {".mp4"}
    db = db_connection()
    res = db.execute("SELECT path FROM video WHERE audio_path IS NULL")
    cnt_found = 0
    cnt_queued = 0
    for row in res:
        path = Path(row[0])
        audio_path = root / (path.name + ".mp3")
        if not path.name.startswith(prefix):
            continue
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

def db_scan_recode(root: Path, prefix=""):
    VIDEO_RECODE_EXT = {".webm", ".mkv"}
    cnt = 0
    futures = []
    for path in root.glob("**/*"):
        if not path.suffix in VIDEO_RECODE_EXT:
            continue
        if not path.name.startswith(prefix):
            continue
        recode_path = root / (path.name + ".mp4")
        if recode_path.exists():
            continue
        f = exec_submit(generate_recode, path, recode_path)
        futures.append(f)
        cnt += 1
    L.info(f"Queued {cnt} videos for recoding.")
    return futures
    
def db_video_remove(path: Path):
    db = db_connection()
    result = db.execute("DELETE FROM video WHERE path = ?", (str(path),))
    L.info(f"Removed {result.rowcount} from DB for {path}.")
    db.commit()

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
    videos = list(db_iter_videos())
    return flask.render_template("gallery.tpl", videos=videos)


@app.route("/delete", methods=["POST"])
def video_del():
    payload = flask.request.get_json()
    src = Path(payload["src"]).relative_to("/video/")
    dst = PTRASH / (src.name + ".del")
    assert (PVIDEOS / src).exists()
    shutil.move(PVIDEOS / src, dst)
    L.info(f"Moved to trash: {src} -> {dst}")
    db_video_remove(PVIDEOS / src)
    return {"status": "OK"}

@app.route("/download/q", methods=["POST"])
def q_put():
    payload = flask.request.get_json()
    url = payload.get("url")
    # Nit: Callbacks are running 3 levels deep here. Better to make this a coro in the future.
    future = exec_submit(generate_download, url, PPILE)
    def cb(future):
        future.result() # re-raise exception
        # Hack
        # We don't have access to the exact file name of the download, but we know it start with today's date.
        # Hence, we re-scan files that start with todays date
        prefix = date.today().isoformat()
        recode_futures = db_scan_recode(PVIDEOS, prefix=prefix)
        def cbb():
            future.result() # re-raise exception
            db_scan_videos(PVIDEOS, prefix=prefix)
            db_scan_poster(PCACHE, prefix=prefix)
            db_scan_audio(PMP3, prefix=prefix)
            db_scan_duration(prefix=prefix)
        all_done_callback(recode_futures, cbb)

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

    # Autoreload
    # app.jinja_env.auto_reload = True
    # app.config["TEMPLATES_AUTO_RELOAD"] = True
    # suppress werkzeug logging. For some reason we have to do this late in the process.
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    socketio.run(app, host="0.0.0.0", port=port, debug=DEBUG, use_reloader=False) # BLOCK

    # CTRL-C will get us here.
    # Cleanup
    executor.shutdown()

if __name__ == "__main__":
    main()
