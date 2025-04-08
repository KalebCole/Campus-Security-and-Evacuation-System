import time
import subprocess
SSID = "iPod Mini"
PASSWORD = "H0t$p0t!"

# Disconnect from the current WiFi
subprocess.run('netsh wlan disconnect', shell=True, check=True)

for attempt in range(5):
    print(f"Attempt {attempt+1} to connect to {SSID}...")
    result = subprocess.run(
        f'netsh wlan connect name="{SSID}"', shell=True, check=True)

    if result.returncode == 0:
        print(f"Successfully connected to {SSID}")
        break
    else:
        print("Connection failed, retrying in 5 seconds...")
        time.sleep(5)
else:
    print(f"Failed to connect to {SSID} after 5 attempts.")
