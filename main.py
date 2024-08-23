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
from apscheduler.schedulers.background import BackgroundScheduler
from concurrent.futures import ThreadPoolExecutor
import subprocess as sp

from sweeper import sweep

logging.basicConfig(
    format="%(asctime)s logger=%(name)s lvl=%(levelname)s pid=%(process)d %(message)s"
)
logging.getLogger("sweeper").setLevel(logging.INFO)

DEBUG = os.environ.get("DEBUG", False)
NO_SWEEP = os.environ.get("NO_SWEEP", False)

L = logging.getLogger(__name__)
L.setLevel(logging.INFO)

if DEBUG:
    L.setLevel(logging.DEBUG)
    L.debug("DEBUG=true")

L.debug(f"NO_SWEEP={NO_SWEEP}")

def validate(env_var, default_path):
    path = Path(os.environ.get(env_var, default_path))
    if DEBUG:
        L.debug(f"{env_var}={path}")
    if not path.is_dir():
        L.error(f"{env_var} does not exist: {path}")
    return path

PVIDEOS= validate("VIDEOS", "./videos")
PPILE= validate("PILE", "./videos/pile")
PMP3= validate("MP3", "./mp3")
PCACHE= validate("CACHE", "./cache")
PTMP= validate("TMP", "./tmp")
PDB = PCACHE / "pile.db"

#
# Helper
#

def pcall(cmd):
    L.debug(f"Running {cmd}")
    p = sp.run(cmd, capture_output=True, check=False)
    if p.returncode != 0:
        L.error(f"Failed running {cmd}")
        L.error(p.stderr)
        L.error(p.stdout)
        return False
    return p


#
# File Actions
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

def generate_download(url, output_dir, log):
    today = date.today().isoformat()
    log(f"Starting download of {url}")
    L.info(f"Download {url}")
    cmd = [
        "yt-dlp",
        "--no-progress",
        "--restrict-filenames",
        "--format",
        "bestvideo[height<=760]+bestaudio",
        "-o",
        f"{output_dir}/{today} %(title)s via %(uploader)s.%(ext)s",
        url,
    ]
    log("[pile-video] " + " ".join(cmd))
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in proc.stdout:
        log("[pile-video] " + line.decode("ASCII").rstrip("\n"))
    code = proc.wait()
    proc.stdout.close()
    if code == 0:
        log(f"[Finished] Downloading {url}.")
    else:
        log(f"[Failed] Downloading {url} with code {code}.")
        for line in proc.stderr:
            log("[pile-video] " + line.decode("ASCII").rstrip("\n"))


#
# Thread Pool Management
#
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
    L.debug(f"socket > {msg}")
    socketio.emit("message", msg, broadcast=True)


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
    print(src)
    print(PVIDEOS / src)
    assert (PVIDEOS / src).exists()
    shutil.move(PVIDEOS / src, PVIDEOS / (str(src) + ".del"))
    L.info(f"Removed from gallery: {src}")
    return {"status": "OK"}


@app.route("/download/q", methods=["POST"])
def q_put():
    payload = flask.request.get_json()
    url = payload.get("url")
    future = exec_submit(generate_download, url, PPILE, websocket_send)
    future.add_done_callback(lambda x: db_scan_recode(PVIDEOS))
    return flask.jsonify({"success": True, "msg": f"Queued download {url}"})

@socketio.on("connect")
def test():
    L.debug("Socket connected")
    socketio.send(f"Welcome!\n")


@socketio.on("message")
def handle_message(msg):
    L.debug(f"Socket received: {msg}")

def exec_interval():
    L.info("Starting update ...")
    subprocess.run(["pip", "install", "-U", "yt-dlp"], capture_output=True, check=True)
    L.info("Update done")

class sched:
    def __init__(self):
        self.sched = BackgroundScheduler()
        self.job_update = None
        self.job_sweep = None

    def start(self):
        self.sched.start()
        self.trigger_update()
        self.trigger_sweep()

    def trigger_update(self):
        L.info("trigger update")
        job = self.job_update
        if job:
            job.remove()
        self.job_update = self.sched.add_job(
            exec_interval,
            "interval",
            seconds=60 * 60,
            max_instances=1,
            next_run_time=datetime.now(),
        )

    def trigger_sweep(self):
        L.info("trigger sweep")
        job = self.job_sweep
        if job:
            job.remove()
        self.job_sweep = self.sched.add_job(
            sweep,
            "interval",
            seconds=60 * 60,
            max_instances=1,
            next_run_time=datetime.now(),
        )

    def shutdown(self):
        if NO_SWEEP:
            return
        self.sched.shutdown()

@click.command()
@click.option("-p", "--port", default=8083, help="Port to listen on", envvar="PORT")
def main(port):
    db_init()

    # Re-scan poster files + audio files on startup
    # db_clear_posters()
    # db_clear_audio()

    db_scan_videos(PVIDEOS)
    db_scan_duration()
    db_scan_poster(PCACHE)
    db_scan_audio(PMP3)
    db_scan_recode(PVIDEOS)

    mysched = sched()
    if NO_SWEEP:
        print("No sweeping no video gallery")
    else:
        mysched.start()

    app.jinja_env.auto_reload = True
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    # suppress werkzeug logging. For some reason we have to do this late in the process.
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    socketio.run(app, host="0.0.0.0", port=port, debug=DEBUG) # blocks

    # CTRL-C will get us here.
    # Cleanup
    mysched.shutdown()
    executor.shutdown()

if __name__ == "__main__":
    main()
