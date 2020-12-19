import json
import subprocess
from queue import Queue

import time
from bottle import run, Bottle, request, static_file, response, redirect, template, get
from threading import Thread
from bottle_websocket import GeventWebSocketServer
from bottle_websocket import websocket
from socket import error

class WSAddr:
    def __init__(self):
        self.wsClassVal = ''

app = Bottle()

port = 8080
proxy = ""

@get('/')
def dl_queue_list():
    return template("./static/template/index.tpl")

@get('/websocket', apply=[websocket])
def echo(ws):
    while True:
        WSAddr.wsClassVal = ws
        msg = WSAddr.wsClassVal.receive()
        if msg is not None:
            a = '[MSG], Started downloading  : '
            a = a + msg
            WSAddr.wsClassVal.send(a)
        else:
            break

@get('/youtube-dl/static/:filename#.*#')
def server_static(filename):
    return static_file(filename, root='./static')

@get('/youtube-dl/q', method='GET')
def q_size():
    return {"success": True, "size": json.dumps(list(dl_q.queue))}

@get('/youtube-dl/q', method='POST')
def q_put():
    url = request.json.get("url")
    resolution = request.json.get("resolution")
    if "" != url:
        box = (url, WSAddr.wsClassVal, resolution, "web")
        dl_q.put(box)
        if (Thr.dl_thread.is_alive() == False):
            thr = Thr()
            thr.restart()
        return {"success": True, "msg": '[MSG], We received your download. Please wait.'}
    else:
        return {"success": False, "msg": "[MSG], download queue somethings wrong."}



@get('/youtube-dl/rest', method='POST')
def q_put_rest():
    url = request.json.get("url")
    resolution = request.json.get("resolution")
    box = (url, "", resolution, "api")
    dl_q.put(box)
    return {"success": True, "msg": 'download has started', "Remaining downloading count": json.dumps(dl_q.qsize()) }

def dl_worker():
    while not done:
        item = dl_q.get()
        if(item[3]=="web"):
            download(item)
        else:
            download_rest(item)
        dl_q.task_done()


def download(url):
    # url[1].send("[MSG], [Started] downloading   " + url[0] + "  resolution below " + url[2])
    result=""
    if (url[2] == "best"):
        result = subprocess.run(["youtube-dl", "--proxy", proxy, "-o", "./downfolder/.incomplete/%(title)s.%(ext)s", "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]", "--exec", "touch {} && mv {} ./downfolder/", "--merge-output-format", "mp4", url[0]])
    elif (url[2] == "audio-m4a"):
         result = subprocess.run(["youtube-dl", "--proxy", proxy, "-o", "./downfolder/.incomplete/%(title)s.%(ext)s", "-f", "bestaudio[ext=m4a]", "--exec", "touch {} && mv {} ./downfolder/", url[0]])
    elif (url[2] == "audio-mp3"):
         result = subprocess.run(["youtube-dl", "--proxy", proxy, "-o", "./downfolder/.incomplete/%(title)s.%(ext)s", "-f", "bestaudio[ext=m4a]", "-x", "--audio-format", "mp3", "--exec", "touch {} && mv {} ./downfolder/", url[0]])
    else:
        resolution = url[2][:-1]
        result = subprocess.run(["youtube-dl", "--proxy", proxy, "-o", "./downfolder/.incomplete/%(title)s.%(ext)s", "-f", "bestvideo[height<="+resolution+"]+bestaudio[ext=m4a]", "--exec", "touch {} && mv {} ./downfolder/",  url[0]])
    try:
        if(result.returncode==0):
            url[1].send("[MSG], [Finished] " + url[0] + "  resolution below " + url[2]+", Remain download Count "+ json.dumps(dl_q.qsize()))
            url[1].send("[QUEUE], Remaining download Count : " + json.dumps(dl_q.qsize()))
            url[1].send("[COMPLETE]," + url[2] + "," + url[0])
        else:
            url[1].send("[MSG], [Finished] downloading  failed  " + url[0])
            url[1].send("[COMPLETE]," + "url access failure" + "," + url[0])
    except error:
        print("Be Thread Safe")


def download_rest(url):
    result=""
    if (url[2] == "best"):
        result = subprocess.run(["youtube-dl", "--proxy", proxy, "-o", "./downfolder/.incomplete/%(title)s.%(ext)s", "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]", "--exec", "touch {} && mv {} ./downfolder/", "--merge-output-format", "mp4", url[0]])
    elif (url[2] == "audio"):
         result = subprocess.run(["youtube-dl", "--proxy", proxy, "-o", "./downfolder/.incomplete/%(title)s.%(ext)s", "-f", "bestaudio[ext=m4a]", "--exec", "touch {} && mv {} ./downfolder/", url[0]])
    else:
        resolution = url[2][:-1]
        result = subprocess.run(["youtube-dl", "--proxy", proxy, "-o", "./downfolder/.incomplete/%(title)s.%(ext)s", "-f", "bestvideo[height<="+resolution+"]+bestaudio[ext=m4a]", "--exec", "touch {} && mv {} ./downfolder/",  url[0]])

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

run(host='0.0.0.0', port=port, server=GeventWebSocketServer)

done = True

Thr.dl_thread.join()
