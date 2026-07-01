from flask import Flask, request
import requests
import re
import urllib.parse
import os
import html

app = Flask(__name__)

token = os.environ.get("TELEGRAM_BOT_TOKEN")
if not token:
    raise RuntimeError("TELEGRAM_BOT_TOKEN env var is not set")

def _maybe_set_webhook():
    base_url = os.environ.get("WEBHOOK_URL") or os.environ.get("RENDER_EXTERNAL_URL")
    if not base_url:
        return

    webhook_url = f"{base_url.rstrip('/')}/{token}"
    try:
        requests.get(
            f"https://api.telegram.org/bot{token}/setWebhook",
            params={"url": webhook_url},
            timeout=10,
        )
        print(f"Webhook set to: {webhook_url}", flush=True)
    except Exception as e:
        print(f"Failed to set webhook: {e}", flush=True)

_maybe_set_webhook()

def find_coords(url: str):
    host = False
    lon = False
    lat = False
    match = re.search(r'(https?:\/\/.*)', url)
    if not match:
        return False, False, False
    url = match.group(1)    
    url = urllib.parse.unquote(url)

    debug_resolve = os.environ.get("DEBUG_RESOLVE") == "1"

    def parse_coords_from_url(u: str):
        parsed = urllib.parse.urlparse(u)
        hostname = (parsed.hostname or "").lower()

        def _first_lon_lat(val: str):
            # Yandex commonly uses lon,lat
            mm = re.search(r"(-?\d+(?:\.\d+)?)[, ]+(-?\d+(?:\.\d+)?)", val)
            if not mm:
                return None
            return mm.group(1), mm.group(2)

        def _first_lat_lon(val: str):
            mm = re.search(r"(-?\d+(?:\.\d+)?)[, ]+(-?\d+(?:\.\d+)?)", val)
            if not mm:
                return None
            return mm.group(1), mm.group(2)

    
        if "yandex" in hostname:
            try:
                qs = urllib.parse.parse_qs(parsed.query)
                
                for key in ("poi[point]", "whatshere[point]", "pt", "ll"):
                    if key in qs and qs[key]:
                        lonlat = _first_lon_lat(qs[key][0])
                        if lonlat:
                            lon, lat = lonlat
                            return lat, lon, "yandex"
            except Exception:
                pass

           
            m = re.search(r"whatshere%5Bpoint%5D=([^&]+)", u, re.I)
            if m:
                lonlat = _first_lon_lat(urllib.parse.unquote(m.group(1)))
                if lonlat:
                    lon, lat = lonlat
                    return lat, lon, "yandex"

        
        if "google" in hostname:
            if "/maps/place/" in u:
                at = re.search(r"@(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)", u)
                pairs = re.findall(r"!3d(-?\d+(?:\.\d+)?)!4d(-?\d+(?:\.\d+)?)", u)
                if at:
                    at_lat, at_lon = float(at.group(1)), float(at.group(2))
                    if pairs:
                       
                        best = None
                        best_d = None
                        for plat_s, plon_s in pairs:
                            plat, plon = float(plat_s), float(plon_s)
                            d = (plat - at_lat) ** 2 + (plon - at_lon) ** 2
                            if best_d is None or d < best_d:
                                best_d = d
                                best = (plat, plon)
                        if best is not None:
                            return str(best[0]), str(best[1]), "google"

                    return str(at_lat), str(at_lon), "google"

            
            m = re.search(r"!3d(-?\d+(?:\.\d+)?)!4d(-?\d+(?:\.\d+)?)", u)
            if m:
                return m.group(1), m.group(2), "google"

            m = re.search(r"@(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)", u)
            if m:
                return m.group(1), m.group(2), "google"

        
        m = re.search(r"/maps/(?:search|place)/(-?\d+(?:\.\d+)?),\+?(-?\d+(?:\.\d+)?)", u)
        if m:
            return m.group(1), m.group(2), "google"

       
        try:
            qs = urllib.parse.parse_qs(parsed.query)
            for key in ("q", "query", "ll", "sll", "center"):
                if key in qs and qs[key]:
                    val = qs[key][0]
                    latlon = _first_lat_lon(val)
                    if latlon:
                        lat, lon = latlon
                        return lat, lon, "google"
        except Exception:
            pass

        return None

    parsed_coords = parse_coords_from_url(url)
    if parsed_coords:
        lat, lon, provider = parsed_coords
        if debug_resolve:
            print(f"coords: provider={provider} lat={lat} lon={lon}", flush=True)
        host = urllib.parse.urlparse(url).hostname or provider
        return host, lat, lon

    
    if True:
        response = requests.get(
            url,
            allow_redirects=True,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        resolved_url = urllib.parse.unquote(response.url or url)
        body = html.unescape(response.text or "")

        def parse_coords_from_html(page: str):
            
            m = re.search(r"!3d(-?\d+(?:\.\d+)?)!4d(-?\d+(?:\.\d+)?)", page)
            if m:
                return m.group(1), m.group(2), "google"
            m = re.search(r"@(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)", page)
            if m:
                return m.group(1), m.group(2), "google"

            
            m = re.search(r'"lat"\s*:\s*(-?\d+(?:\.\d+)?)\s*,\s*"lng"\s*:\s*(-?\d+(?:\.\d+)?)', page)
            if m:
                return m.group(1), m.group(2), "google"
            m = re.search(r'"lng"\s*:\s*(-?\d+(?:\.\d+)?)\s*,\s*"lat"\s*:\s*(-?\d+(?:\.\d+)?)', page)
            if m:
                return m.group(2), m.group(1), "google"

           
            m = re.search(r'"center"\s*:\s*\[\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\]', page)
            if m:
                return m.group(1), m.group(2), "google"
            return None

        
        if (
            "maps.app.goo.gl" in resolved_url
            or "goo.gl/maps" in resolved_url
            or "yandex" in (urllib.parse.urlparse(resolved_url).hostname or "").lower()
        ):
           
            def _pick_first(matches):
                for candidate in matches:
                    if not candidate:
                        continue
                    return candidate
                return None

           
            m = re.search(r'rel=["\']canonical["\']\s+href=["\']([^"\']+)["\']', body, re.I)
            if not m:
                m = re.search(r'property=["\']og:url["\']\s+content=["\']([^"\']+)["\']', body, re.I)

            if not m:
                m = re.search(r'(https?://www\.google\.[^/]+/maps[^"\'<>\s]+)', body, re.I)
            if not m:
                m = re.search(r'(https?://maps\.google\.[^/]+/maps[^"\'<>\s]+)', body, re.I)
            if not m:
                m = re.search(r'(https?://yandex\.[^/]+/(?:maps|navi)[^"\'<>\s]+)', body, re.I)

            
            if not m:
                m = re.search(r'http-equiv=["\']refresh["\']\s+content=["\'][^"\']*url=([^"\']+)["\']', body, re.I)

           
            if not m:
                m = re.search(r'location\.(?:href|replace)\s*=\s*["\']([^"\']+)["\']', body, re.I)
            if not m:
                m = re.search(r'window\.location\.(?:href|replace)\s*\(\s*["\']([^"\']+)["\']\s*\)', body, re.I)

            
            if not m:
                encoded_hits = re.findall(
                    r'(https%3A%2F%2F(?:www%2E)?google%2E[^%]+%2Fmaps[^"\'<>\s]+)',
                    body,
                    re.I,
                )
                decoded = _pick_first([urllib.parse.unquote(h) for h in encoded_hits])
                if decoded:
                    m = re.match(r"(.+)", decoded)

            if m:
                resolved_url = urllib.parse.unquote(m.group(1))

        if debug_resolve:
            print(f"resolve: in={url} final={resolved_url} status={response.status_code}", flush=True)
            loc = response.headers.get("location") or response.headers.get("Location")
            if loc:
                print(f"resolve: header-location={loc}", flush=True)
            print(f"resolve: content-type={response.headers.get('content-type')}", flush=True)

        url = resolved_url

        
        parsed_final = urllib.parse.urlparse(url)
        final_host = (parsed_final.hostname or "").lower()
        if "yandex" in final_host and ("showcaptcha" in parsed_final.path or "showcaptcha" in url):
            if debug_resolve:
                print("resolve: yandex captcha detected", flush=True)
            return "yandex_captcha", False, False

        parsed_coords = parse_coords_from_url(url)

        
        if not parsed_coords and "google" in (urllib.parse.urlparse(url).hostname or "").lower():
            parsed_coords = parse_coords_from_html(body)
            if debug_resolve and parsed_coords:
                lat, lon, _ = parsed_coords
                print(f"coords: source=html lat={lat} lon={lon}", flush=True)

        if not parsed_coords and "google" in (urllib.parse.urlparse(url).hostname or "").lower():
            try:
                qs = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
                qval = qs.get("q", [None])[0] or qs.get("query", [None])[0]
                if qval:
                    resp2 = requests.get(
                        "https://www.google.com/maps/search/",
                        params={"api": "1", "query": qval},
                        allow_redirects=True,
                        timeout=15,
                        headers={"User-Agent": "Mozilla/5.0"},
                    )
                    url2 = urllib.parse.unquote(resp2.url or "")
                    body2 = html.unescape(resp2.text or "")
                    if debug_resolve:
                        print(f"resolve2: query={qval} final={url2} status={resp2.status_code}", flush=True)
                    parsed_coords = parse_coords_from_url(url2) or parse_coords_from_html(body2)

                if not parsed_coords:
                    ftid = qs.get("ftid", [None])[0]
                    if ftid and ":" in ftid:
                        try:
                            cid_hex = ftid.split(":", 1)[1]
                            cid = int(cid_hex, 16)
                            resp3 = requests.get(
                                "https://www.google.com/maps",
                                params={"cid": str(cid)},
                                allow_redirects=True,
                                timeout=15,
                                headers={"User-Agent": "Mozilla/5.0"},
                            )
                            url3 = urllib.parse.unquote(resp3.url or "")
                            body3 = html.unescape(resp3.text or "")
                            if debug_resolve:
                                print(f"resolve3: cid={cid} final={url3} status={resp3.status_code}", flush=True)
                            parsed_coords = parse_coords_from_url(url3) or parse_coords_from_html(body3)
                        except Exception as e:
                            if debug_resolve:
                                print(f"resolve3: failed {e}", flush=True)
            except Exception as e:
                if debug_resolve:
                    print(f"resolve2: failed {e}", flush=True)

    if parsed_coords:
        lat, lon, provider = parsed_coords
        if debug_resolve:
            print(f"coords: provider={provider} lat={lat} lon={lon}", flush=True)
        host = urllib.parse.urlparse(url).hostname or provider
    return host, lat, lon

def sendMessage(chatId, text):
    requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                  params={"chat_id": chatId, "text": text})

def sendLocation(chatId, lat, lon):
    requests.post(f"https://api.telegram.org/bot{token}/sendLocation",
                  params={"chat_id": chatId, "latitude": lat, "longitude": lon})

@app.get("/")
def health():
    return "OK"

@app.route(f"/{token}", methods=["POST"])
def webhook():
    data = request.get_json()
    if not data or "message" not in data:
        return "OK"

    message = data["message"]
    chatId = message["chat"]["id"]
    print(f"Incoming update: {data}", flush=True)

    if "text" in message:
        text = message["text"]
        if "/start" in text:
            sendMessage(chatId, "Salom! Location yuboring")
        else:
            host, lat, lon = find_coords(text)
            if host == "yandex_captcha":
                sendMessage(
                    chatId,
                    "Yandex linkni server tomonda ochishda CAPTCHA chiqyapti. "
                    "Iltimos Yandex ilovada/браузерda linkni ochib, Share/Поделиться qilib "
                    "chiqqan to‘liq linkni yuboring (unda ll yoki poi[point] bo‘ladi), "
                    "yoki shunchaki Location (pin) yuboring.",
                )
            elif host and lat and lon:
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



