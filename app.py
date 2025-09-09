from flask import Flask, request
import requests
import re
import urllib.parse
import os

app = Flask(__name__)

token = os.environ.get("TELEGRAM_BOT_TOKEN")

def find_coords(url: str):
    host = False
    lon = False
    lat = False
    if not url.startswith("http"):
        return False, False, False
    url = urllib.parse.unquote(url)
    regex = r"[@=](\d+)\.(\d+),(\d+)\.(\d+)"
    regex2 = r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)"
    match = re.search(regex, url)
    if not match:
        response = requests.get(url)
        url = urllib.parse.unquote(response.url)
        if "utm_source" in url: 
            match = re.search(regex2,url)
        else:
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

def sendMessage(chatId, text):
    requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                  params={"chat_id": chatId, "text": text})

def sendLocation(chatId, lat, lon):
    requests.post(f"https://api.telegram.org/bot{token}/sendLocation",
                  params={"chat_id": chatId, "latitude": lat, "longitude": lon})

@app.route(f"/{token}", methods=["POST"])
def webhook():
    data = request.get_json()
    if not data or "message" not in data:
        return "OK"

    message = data["message"]
    chatId = message["chat"]["id"]

    if "text" in message:
        text = message["text"]
        if "/start" in text:
            sendMessage(chatId, "Salom! Location yuboring")
        else:
            host, lat, lon = find_coords(text)
            if host and lat and lon:
                sendLocation(chatId, lat, lon)
                if "google" in host:
                    yandex_link = f"https://yandex.com/navi?whatshere%5Bpoint%5D={lon}%2C{lat}"
                    sendMessage(chatId, yandex_link)
                elif "yandex" in host:
                    google_link = f"https://www.google.com/maps?q={lat},{lon}" 
                    sendMessage(chatId, google_link)
            else:
                sendMessage(chatId, "Iltimos, to‘g‘ri Google yoki Yandex link yuboring")
    elif "location" in message:
        lon = message["location"]["longitude"]
        lat = message["location"]["latitude"]
        yandex_link = f"https://yandex.com/navi?whatshere%5Bpoint%5D={lon}%2C{lat}"
        google_link = f"https://www.google.com/maps?q={lat},{lon}"
        sendMessage(chatId, yandex_link)
        sendMessage(chatId, google_link)

    return "OK"





