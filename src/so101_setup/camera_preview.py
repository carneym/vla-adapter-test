"""A local browser preview for positioning one camera; never accesses arm ports."""

import json
import math
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .config import CAMERA_WARMUP_S, load_config


PAGE = """<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Robot camera preview</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#101519;color:#f2f5f7;font:16px system-ui,sans-serif}
main{max-width:1100px;margin:auto;padding:24px}header{display:flex;align-items:center;justify-content:space-between;gap:16px}
h1{font-size:24px;margin:0}p{color:#b9c8d0;line-height:1.5}button{background:#e8f1f5;color:#18242c;border:0;border-radius:8px;padding:12px 18px;font:inherit;cursor:pointer}
.view{position:relative;background:#000;border-radius:12px;overflow:hidden;margin:24px 0}img{display:block;width:100%;aspect-ratio:4/3;object-fit:contain}
.cross{position:absolute;left:50%;top:50%;width:24px;height:24px;transform:translate(-50%,-50%);pointer-events:none;opacity:.6}
.cross:before,.cross:after{content:"";position:absolute;background:white;box-shadow:0 0 2px black}.cross:before{width:24px;height:1px;top:12px}.cross:after{height:24px;width:1px;left:12px}
#status{font-size:14px;color:#9fe1bc}button:disabled{opacity:.5;cursor:default}
</style>
<main><header><div><h1>CAMERA_TITLE camera</h1><p id="status">Connecting…</p></div><button id="stop">Stop camera</button></header>
<div class="view"><img id="feed" src="stream" alt="Live robot camera"><span class="cross"></span></div>
<p>Adjust the camera so the gripper, task surface, and full raised position stay in view.</p>
<p>Local preview · No recording · Arm control is inactive in this preview</p></main>
<script>
const status=document.querySelector('#status'), stop=document.querySelector('#stop'), feed=document.querySelector('#feed');
let ended=false;
function finish(message){ended=true;status.textContent=message;stop.disabled=true;feed.removeAttribute('src');}
stop.onclick=async()=>{try{const r=await fetch('stop',{method:'POST'});if(!r.ok)throw Error();finish('Camera stopped.');}catch(e){finish('Preview disconnected.');}};
async function health(){if(ended)return;try{const r=await fetch('status',{cache:'no-store'});if(!r.ok)throw Error();const s=await r.json();if(!s.live){finish('Camera stopped delivering frames.');return;}status.textContent='Live · '+s.width+' × '+s.height+' · preview up to 15 fps';}catch(e){finish('Preview ended. Restart the camera-preview command to reconnect.');}}
setInterval(health,1000);health();
</script></html>"""


def camera_preview(root, name="overhead", duration=1800):
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Preview duration must be a finite positive number of seconds.")
    matches = [c for c in load_config(root)["cameras"] if c["name"] == name]
    if len(matches) != 1 or name not in ("overhead", "wrist"):
        raise ValueError("Select one configured overhead or wrist camera.")
    settings = matches[0]
    if type(settings.get("device")) is not int or settings["device"] < 0:
        raise ValueError(f"Configure the {name} camera index first.")
    for field in ("capture_width", "capture_height", "fps"):
        if type(settings.get(field)) is not int or settings[field] <= 0:
            raise ValueError(f"Configure a positive {field} for {name}.")

    import cv2
    from lerobot.cameras.opencv import OpenCVCamera, OpenCVCameraConfig

    camera = OpenCVCamera(OpenCVCameraConfig(
        index_or_path=settings["device"], width=settings["capture_width"],
        height=settings["capture_height"], fps=settings["fps"], warmup_s=CAMERA_WARMUP_S,
    ))
    stopped = threading.Event()
    prefix = "/" + secrets.token_urlsafe(24) + "/"
    server = timer = None

    def latest():
        with camera.frame_lock:
            stamp, frame = camera.latest_timestamp, camera.latest_frame
        live = (camera.thread is not None and camera.thread.is_alive()
                and stamp is not None and frame is not None and time.perf_counter() - stamp < 2)
        return live, stamp, frame

    def stop():
        stopped.set()
        server.shutdown()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def reply(self, content, content_type):
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            self.wfile.write(content)

        def do_GET(self):
            try:
                if self.path == prefix:
                    self.reply(PAGE.replace("CAMERA_TITLE", name.capitalize()).encode(), "text/html; charset=utf-8")
                elif self.path == prefix + "status":
                    live, _, _ = latest()
                    self.reply(json.dumps({"live": live and not stopped.is_set(),
                                           "width": camera.width, "height": camera.height}).encode(), "application/json")
                elif self.path == prefix + "stream":
                    self.send_response(200)
                    self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    previous = None
                    while not stopped.is_set():
                        live, stamp, frame = latest()
                        if not live:
                            break
                        if stamp != previous:
                            ok, jpeg = cv2.imencode(".jpg", cv2.cvtColor(frame, cv2.COLOR_RGB2BGR),
                                                   [cv2.IMWRITE_JPEG_QUALITY, 85])
                            if not ok:
                                break
                            data = jpeg.tobytes()
                            self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: "
                                             + str(len(data)).encode() + b"\r\n\r\n" + data + b"\r\n")
                            self.wfile.flush()
                            previous = stamp
                        stopped.wait(1 / 15)
                else:
                    self.send_error(404)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_POST(self):
            if self.path != prefix + "stop":
                self.send_error(404)
                return
            self.reply(b"Stopped", "text/plain")
            threading.Thread(target=stop, daemon=True).start()

    try:
        print(f"Opening {name} camera (index {settings['device']}); no arm access...", flush=True)
        camera.connect()
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        timer = threading.Timer(duration, stop)
        timer.daemon = True
        timer.start()
        print(f"Preview: http://127.0.0.1:{server.server_port}{prefix}", flush=True)
        print(f"Use Stop camera or Ctrl+C to close. Automatic stop after {duration / 60:g} minutes.", flush=True)
        server.serve_forever(poll_interval=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        stopped.set()
        if timer is not None:
            timer.cancel()
        if server is not None:
            server.server_close()
        if camera.is_connected or camera.thread is not None:
            camera.disconnect()
        print("Preview closed; camera released.", flush=True)
