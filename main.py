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
from apscheduler.schedulers.background import BackgroundScheduler

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
if DEBUG:
    L.debug("DEBUG=true")

L.debug(f"NO_SWEEP={NO_SWEEP}")

dl_q = Queue()
dl_done = False
dl_thread = None


mysched = None
PVIDEOS = Path("./videos")


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
    return flask.send_from_directory("./videos", filepath)


@app.route("/poster/<path:filepath>")
def serve_poster(filepath):
    return flask.send_from_directory("./cache", filepath)


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
        for p in Path("./videos").glob("**/*")
        if (p.suffix in VIDEO_EXT) and (not p.name.startswith("."))
    ]

    def key(o):
        p, m = o
        if m:
            return "y" + p.name
        else:
            return "x"

    paths = sorted(paths, reverse=True, key=key)
    videos = [
        {
            "name": o[0].name,
            "src": "/video/" + "/".join(o[0].parts[1:]),
            "poster": "/poster/" + o[0].parts[-1] + ".png",
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
    "Enqueue a video download request"
    global dl_thread
    payload = flask.request.get_json()
    url = payload.get("url")
    av = payload.get("av")
    if "" != url:
        req = {"url": url, "av": av}
        dl_q.put(req)
        websocket_send(f"Queued {url}. Total={dl_q.qsize()}")
        if dl_thread and not dl_thread.is_alive():
            dl_thread = Thread(target=dl_worker)
            dl_thread.start()
        return flask.jsonify({"success": True, "msg": f"Queued download {url}"})
    else:
        return flask.jsonify({"success": False, "msg": "Failed"})


@socketio.on("connect")
def test():
    L.debug("Socket connected")
    socketio.send(f"Downloads queued {dl_q.qsize()}\n")


@socketio.on("message")
def handle_message(msg):
    L.debug(f"Socket received: {msg}")


def download(req):
    today = date.today().isoformat()
    url = req["url"]
    av = req["av"]
    websocket_send(f"Starting download of {url}")
    L.info(f"Download {url}")
    if av == "A":  # audio only
        cmd = [
            "yt-dlp",
            "--no-progress",
            "--restrict-filenames",
            "--format",
            "bestaudio",
            "-o",
            f"./mp3/{today} %(title)s via %(uploader)s.audio.%(ext)s",
            "--extract-audio",
            "--audio-format",
            "mp3",
            url,
        ]
    else:
        cmd = [
            "yt-dlp",
            "--no-progress",
            "--restrict-filenames",
            "--format",
            "bestvideo[height<=760]+bestaudio",
            # Often sensible video and audio streams are only available separately,
            # so we need to merge the resulting file. Recoding a video to mp4
            # with A+V can take a lot of time, so we opt for an open container format:
            # Option A: Recode Video
            # "--recode-video", "mp4",
            # "--postprocessor-args", "-strict experimental", # allow use of mp4 encoder
            # Option B: Use container format
            # "--merge-output-format", "webm",
            "-o",
            f"./videos/pile/{today} %(title)s via %(uploader)s.%(ext)s",
            url,
            # "--verbose",
        ]
    websocket_send("[pile-video] " + " ".join(cmd))
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in proc.stdout:
        websocket_send("[pile-video] " + line.decode("ASCII").rstrip("\n"))
    code = proc.wait()
    proc.stdout.close()
    try:
        if code == 0:
            websocket_send(
                "[Finished] " + url + ". Remaining: " + json.dumps(dl_q.qsize())
            )
        else:
            websocket_send("[Failed] " + url)
            return
    except error as e:
        L.error(e)
        websocket_send("[Failed]" + str(e))
        return
    mysched.trigger_sweep()
    websocket_send("Done.")


def dl_worker():
    L.info("Worker starting")
    while not dl_done:
        item = dl_q.get()
        download(item)
        dl_q.task_done()


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
        if NO_SWEEP:
            return
        self.sched.start()
        self.trigger_update()
        self.trigger_sweep()
        self.sched.add_job(
            exec_counter_commit,
            "interval",
            seconds=10,
            max_instances=1,
            next_run_time=datetime.now(),
        )

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


if __name__ == "__main__":
    dl_thread = Thread(target=dl_worker)
    dl_thread.start()
    mysched = sched()
    mysched.start()
    app.jinja_env.auto_reload = True
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    # suppress werkzeug logging. For some reason we have to do this late in the process.
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    socketio.run(app, host="0.0.0.0", port=8083)
    # Cleanup
    mysched.shutdown()
    dl_done = True
    dl_thread.join()
