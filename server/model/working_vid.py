import picoweb
import utime
import camera
import gc
ss = ""
pas = ""
SSID = ss         # Enter your WiFi name
PASSWORD = pas     # Enter your WiFi password

def wifi_connect():
    import network
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('connecting to network...')
        wlan.connect(SSID, PASSWORD) 
    start = utime.time()
    while not wlan.isconnected():
        utime.sleep(1)
        if utime.time()-start > 5:
            print("connect timeout!")
            break
    if wlan.isconnected():
        print('network config:', wlan.ifconfig()) # can get rid of this in future just need to check wifi connection for now

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
    camera.saturation(0) #camera set up recommendation from github
    camera.brightness(0)
    camera.contrast(0)
    camera.quality(10)
    camera.speffect(camera.EFFECT_NONE)
    camera.whitebalance(camera.WB_NONE)
    
    
"""    not needed- shows video livestream
here was where the web was hosted
"""

"""
def index(req, resp):
    yield from resp.awrite(index_web) index web was deleted, can add it back if necessary - just html
"""
def send_frame(): # maybe only need this for image capture / forwarding
    buf = camera.capture()
    yield (b'--frame\r\n'
           b'Content-Type: image/jpeg\r\n\r\n'
           + buf + b'\r\n')
    del buf
    gc.collect()

def video(req, resp): # does the video stream, may not need this
    yield from picoweb.start_response(resp, content_type="multipart/x-mixed-replace; boundary=frame")
    while True:
        yield from resp.awrite(next(send_frame()))
        gc.collect()

def capture(req, resp): #takes single picture
    buf = camera.capture()
    yield from picoweb.start_response(resp, content_type="image/jpeg")
    yield from resp.awrite(buf)
    del buf
    gc.collect()

def get_session(): #not sure if works from chat
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
    
    
def send_image(session_id): #not sure if works, from chat
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
    #("/", index), just for html showcase, no longer needed
    ("/video", video),
    ("/capture", capture),
]

if __name__ == '__main__': #testing the stuff
    camera_init()
    wifi_connect()
    app = picoweb.WebApp(__name__, ROUTES)
    app.run(debug=1, port=80, host="0.0.0.0")

