import json
import subprocess
from queue import Queue
import io
import sys
from pathlib import Path
import re

from datetime import date
from bottle import run, Bottle, request, static_file, response, redirect, template, get
from threading import Thread
from bottle_websocket import GeventWebSocketServer
from bottle_websocket import websocket
from socket import error

class WSAddr:
    def __init__(self):
        self.wsClassVal = ''

import bottle
bottle.debug(True)

app = Bottle()
port = 8080
proxy = ""

def L(*args):
    print(*args, file=sys.stderr)

WS = []
def send(msg):
    for ws in WS.copy():
        try:
            L("> " + msg)
            ws.send(msg)
        except error as e:
            L(f"> ws {ws} failed. Closing.")
            if ws in WS:
                WS.remove(ws)


def pcall(cmd):
    send(f"Running {cmd}")
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="ASCII")
    if p.returncode != 0:
        msg = f"Error executing {cmd}\ncode:{p.returncode}\nout:{p.stdout}\nerr:{p.stderr}"
        send(msg)
        raise Exception(msg)
    return p


@get('/')
def dl_queue_list():
    return template("./static/template/index.tpl")

@get('/gallery')
def gallery():
    VIDEO_EXT = { ".mkv", ".webm", ".mp4" }
    paths = [
        p for p in Path("./videos").glob('**/*') if
        (p.suffix in VIDEO_EXT)
        and
        ( not p.name.startswith("."))
    ]
    re_date = re.compile("\d\d\d\d\-\d\d-\d\d.*")
    A = []
    B = []
    for p in paths:
        if re_date.match(p.name):
            A.append(p)
        else:
            B.append(p)
    A = sorted(A, reverse=True)
    paths = A + B
    videos = [
        {
            "name" : p.name,
            "src"  : "/video/" + "/".join(p.parts[1:])
        }
        for p in paths
    ]
    return template("./static/template/gallery.tpl", { "videos" : videos })

@get('/video/<filepath:path>')
def video(filepath):
    return static_file(filepath, root='./videos')

@get('/websocket', apply=[websocket])
def echo(ws):
    L(f"New WebSocket {ws} total={len(WS)}")
    WS.append(ws)
    # need to receive once so socket gets not closed
    L(ws.receive())
    ws.send(f"Downloads queued {dl_q.qsize()}\n")

@get('/youtube-dl/static/<filepath:path>')
def server_static(filepath):
    return static_file(filepath, root='./static')

@get('/youtube-dl/q', method='GET')
def q_size():
    return {"success": True, "size": json.dumps(list(dl_q.queue))}

@get('/youtube-dl/q', method='POST')
def q_put():
    url = request.json.get("url")
    resolution = request.json.get("resolution")
    if "" != url:
        box = (url, None, resolution, "web")
        dl_q.put(box)
        send(f"Queued {url}. Total={dl_q.qsize()}")
        if (Thr.dl_thread.is_alive() == False):
            thr = Thr()
            thr.restart()
        return {"success": True, "msg": f"Queued download {url}"}
    else:
        return {"success": False, "msg": "Failed"}

@get('/youtube-dl/rest', method='POST')
def q_put_rest():
    url = request.json.get("url")
    resolution = request.json.get("resolution")
    box = (url, "", resolution, "api")
    dl_q.put(box)
    return {"success": True, "msg": 'download has started', "Remaining downloading count": json.dumps(dl_q.qsize()) }

def dl_worker():
    L("Worker starting")
    while not done:
        item = dl_q.get()
        download(item)
        dl_q.task_done()

def download(box):
    today = date.today().isoformat()
    url = box[0]
    ws = box[1]
    # result = subprocess.run()
    send(f"Starting download of {url}")
    cmd = [
    "youtube-dl",
        "--no-progress",
        "--restrict-filenames",
        "--format", "bestvideo[height<=760]+bestaudio",
        # Often sensible video and audio streams are only available separately,
        # so we need to merge the resulting file. Recoding a video to mp4
        # with A+V can take a lot of time, so we opt for an open container format:
        # Option A: Recode Video
        # "--recode-video", "mp4",
        # "--postprocessor-args", "-strict experimental", # allow use of mp4 encoder
        # Option B: Use container format
        # "--merge-output-format", "webm",
        "-o", f"./downloads/{today} %(title)s via %(uploader)s.%(ext)s",
        url,
        # "--verbose",
    ]
    send("[youtube-dl] " + " ".join(cmd))
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in proc.stdout:
        send("[youtube-dl] " + line.decode("ASCII").rstrip("\n"))
    code = proc.wait()
    proc.stdout.close()
    try:
        if(code==0):
            send("[Finished] " + url + ". Remaining: "+ json.dumps(dl_q.qsize()))
        else:
            send("[Failed] " + url)
            return
    except error as e:
        L(e)
        send("[Failed]" + str(e))
        return

    p = pcall(cmd + ["--get-filename"])
    fn = p.stdout.rstrip("\n")
    # The filename is not actually accurate. The extension might be wrongly detected.
    # Let's glob this:
    fn = str(list(Path(".").glob(str(Path(fn).with_suffix("")) + "*"))[0])
    p = pcall([
            "ffmpeg", "-y", "-i", fn,
            "-ss", "00:00:20.000", "-vframes", "1",
            fn + ".png"
    ])
    send("Done.")

class Thr:
    def __init__(self):
        self.dl_thread = ''

    def restart(self):
        self.dl_thread = Thread(target=dl_worker)
        self.dl_thread.start()

dl_q = Queue()
done = False
Thr.dl_thread = Thread(target=dl_worker)
Thr.dl_thread.start()

run(host='0.0.0.0', port=port, server=GeventWebSocketServer, reloader=True)

done = True

Thr.dl_thread.join()
 
