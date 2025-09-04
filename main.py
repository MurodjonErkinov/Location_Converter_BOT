import requests
import re
import urllib.parse
import time

def find_coords(url: str):
    host = False
    lon = False
    lat = False
    if not url.startswith("http"):
        return False, False, False
    url = urllib.parse.unquote(url)
    regex = r"[@=](\d+)\.(\d+),(\d+)\.(\d+)"
    match = re.search(regex, url)
    if not match:
        response = requests.get(url)
        url = urllib.parse.unquote(response.url)
        match = re.search(regex, url)
    if match:
        host = urllib.parse.urlparse(url).hostname
        if "google" in host:
            lat = match.group(1) + "." + match.group(2)
            lon = match.group(3) + "." + match.group(4)
        elif "yandex" in host:
            lon = match.group(1) + "." + match.group(2)
            lat = match.group(3) + "." + match.group(4)
    return host, lat, lon

token = "7958597397:AAGzsI6L4Ug9xl1UEfRqx6z81d53kZT-k0s"
url = f"https://api.telegram.org/bot{token}/getUpdates"
last_update_id = 0

while True:
    response = requests.get(url, params={"offset": last_update_id + 1})
    data = response.json()

    for update in data.get("result", []):
        last_update_id = update["update_id"]
        chatId = update["message"]["chat"]["id"]
        if "text" in update["message"]:
            text = update["message"]["text"]
            if "/start" in text:
                requests.post(url=f"https://api.telegram.org/bot{token}/sendMessage",params={"chat_id": chatId, "text": "Salom! Link yuboring"})
                continue
            host, lat, lon = find_coords(text)
            print(host, lat, lon, chatId)
            if host and lat and lon:
                requests.post(url=f"https://api.telegram.org/bot{token}/sendLocation",params={"chat_id": chatId,"latitude": lat,"longitude": lon})
                if "google" in host:
                    yandex_link = f"https://yandex.com/navi?whatshere%5Bpoint%5D={lon}%2C{lat}"
                    requests.post(url=f"https://api.telegram.org/bot{token}/sendMessage",params={"chat_id":chatId,"text":yandex_link})
                elif "yandex" in host:
                    google_link = f"https://www.google.com/maps?q={lat},{lon}" 
                    requests.post(url=f"https://api.telegram.org/bot{token}/sendMessage",params={"chat_id":chatId,"text":google_link})
                continue
        if "location" in update["message"]:
            lon = update["message"]["location"]["longitude"]
            lat = update["message"]["location"]["latitude"]
            yandex_link = f"https://yandex.com/navi?whatshere%5Bpoint%5D={lon}%2C{lat}"
            requests.post(url=f"https://api.telegram.org/bot{token}/sendMessage",params={"chat_id":chatId,"text":yandex_link})
            google_link = f"https://www.google.com/maps?q={lat},{lon}" 
            requests.post(url=f"https://api.telegram.org/bot{token}/sendMessage",params={"chat_id":chatId,"text":google_link})
            continue
        requests.post(url=f"https://api.telegram.org/bot{token}/sendMessage",params={"chat_id": chatId,"text": "Salom! To'gri LOCATION yuboring"})
    time.sleep(2)
