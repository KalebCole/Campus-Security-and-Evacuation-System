import picoweb
import utime
import camera
import gc
import ujson

SSID = "TJ's iPhone"         # Enter your WiFi name
PASSWORD = "W7mshsuwb"     # Enter your WiFi password
#SERVER_URL = "http://your-server.com"

def wifi_connect():
    import network
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('connecting to network...')
        wlan.ifconfig(('192.168.1.100', '255.255.255.0', '192.168.1.1', '8.8.8.8'))
        wlan.connect(SSID, PASSWORD)
    start = utime.time()
    while not wlan.isconnected():
        utime.sleep(1)
        if utime.time()-start > 5:
            print("connect timeout!")
            break
    if wlan.isconnected():
        print('network config:', wlan.ifconfig())

def camera_init():
    camera.deinit()
    camera.init(0, d0=4, d1=5, d2=18, d3=19, d4=36, d5=39, d6=34, d7=35,
                format=camera.JPEG, framesize=camera.FRAME_VGA, 
                xclk_freq=camera.XCLK_20MHz,
                href=23, vsync=25, reset=-1, pwdn=-1,
                sioc=27, siod=26, xclk=21, pclk=22, fb_location=camera.PSRAM)
    camera.framesize(camera.FRAME_VGA)
    camera.flip(1)
    camera.mirror(1)
    camera.saturation(0)
    camera.brightness(0)
    camera.contrast(0)
    camera.quality(10)
    camera.speffect(camera.EFFECT_NONE)
    camera.whitebalance(camera.WB_NONE)

index_web="""
HTTP/1.0 200 OK\r\n
<html>
  <head>
    <title>Video Streaming</title>
  </head>
  <body>
    <h1>Video Streaming Demonstration</h1>
    <img src="/video" style="transform:rotate(180deg);" />
    <br>
    <button onclick="window.location.href='/capture'">Take Picture</button>
  </body>
</html>
"""

def index(req, resp):
    yield from resp.awrite(index_web)

def send_frame():
    buf = camera.capture()
    yield (b'--frame\r\n'
           b'Content-Type: image/jpeg\r\n\r\n'
           + buf + b'\r\n')
    del buf
    gc.collect()

def video(req, resp):
    yield from picoweb.start_response(resp, content_type="multipart/x-mixed-replace; boundary=frame")
    while True:
        yield from resp.awrite(next(send_frame()))
        gc.collect()

def capture(req, resp):
    buf = camera.capture()
    yield from picoweb.start_response(resp, content_type="image/jpeg")
    yield from resp.awrite(buf)
    del buf
    gc.collect()

def get_session():
    try:
        response = urequests.post(SERVER_URL + "/api/session")
        if response.status_code == 200:
            session_data = ujson.loads(response.text)
            return session_data.get("session_id")
        else:
            print("Failed to get session ID")
            return None
    except Exception as e:
        print("Error getting session ID:", str(e))
        return None

def send_image(session_id):
    try:
        buf = camera.capture()
        headers = {"Content-Type": "image/jpeg"}
        response = urequests.post(SERVER_URL + "/api/image", headers=headers, data=buf, params={"session_id": session_id})
        if response.status_code == 200:
            print("Image successfully uploaded")
        else:
            print("Failed to upload image")
        del buf
        gc.collect()
    except Exception as e:
        print("Error uploading image:", str(e))

ROUTES = [
    ("/", index),
    ("/video", video),
    ("/capture", capture),
]

if __name__ == '__main__':
    import socket

    addr = ("192.168.1.100", 8080)  # Replace with your PC's IP
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(addr)

    sock.send(b"Hello from ESP32!\n")
    sock.close()

    camera_init()
    wifi_connect()
    """
    session_id = get_session()
    if session_id:
        send_image(session_id)
        
        
    """
    app = picoweb.WebApp(__name__, ROUTES)
    app.run(debug=0, port=80, host="0.0.0.0")
