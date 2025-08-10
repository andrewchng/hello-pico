# Pico W HTTP LED control on GP15
# Fill in your Wi-Fi credentials below and run this script.

import network
import socket
import time
from machine import Pin

# Load Wi‑Fi credentials from external file to avoid hardcoding in code
try:
    import secrets  # file secrets.py with WIFI_SSID and WIFI_PASSWORD
    SSID = secrets.WIFI_SSID
    PASSWORD = secrets.WIFI_PASSWORD
except Exception:
    raise RuntimeError(
        "Missing secrets.py. Create a file 'secrets.py' with WIFI_SSID and WIFI_PASSWORD."
    )

led = Pin(15, Pin.OUT)  # External LED on GP15 (with series resistor to GND)


def connect_wifi(timeout_ms=15000):
    print("Connecting to Wi-Fi...")
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(SSID, PASSWORD)
        start = time.ticks_ms()
        while not wlan.isconnected() and time.ticks_diff(time.ticks_ms(), start) < timeout_ms:
            time.sleep_ms(200)
    if not wlan.isconnected():
        raise RuntimeError("WiFi connection failed. Check SSID/PASSWORD.")
    ip, _, _, _ = wlan.ifconfig()
    return ip


def html_page(state):
    # Keep HTML tiny to reduce memory usage
    state_text = "ON" if state else "OFF"
    body = (
        "<!doctype html>\n"
        "<html><head><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<title>Pico W LED</title></head><body>"
        "<h1>Pico W LED: " + state_text + "</h1>"
        "<p>"
        "<a href=\"/on\"><button>ON</button></a> "
        "<a href=\"/off\"><button>OFF</button></a> "
        "<a href=\"/toggle\"><button>TOGGLE</button></a>"
        "</p>"
        "</body></html>"
    )
    headers = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: text/html; charset=utf-8\r\n"
        "Content-Length: " + str(len(body)) + "\r\n"
        "Connection: close\r\n\r\n"
    )
    return (headers + body).encode()


def serve_forever(ip, port=80):
    addr = socket.getaddrinfo("0.0.0.0", port)[0][-1]
    s = socket.socket()
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    except Exception:
        pass
    s.bind(addr)
    s.listen(2)
    print("Open in your browser: http://%s/" % ip)

    try:
        while True:
            cl, remote = s.accept()
            try:
                req = cl.recv(1024) or b""
                first = req.split(b"\r\n", 1)[0]
                parts = first.split()
                method = parts[0] if len(parts) >= 1 else b"GET"
                path = parts[1] if len(parts) >= 2 else b"/"

                # Basic access log
                try:
                    print("[HTTP]", remote, method, path)
                except Exception:
                    pass

                if path == b"/favicon.ico":
                    cl.sendall(b"HTTP/1.1 204 No Content\r\nConnection: close\r\n\r\n")
                else:
                    if path == b"/on":
                        led.value(1)
                    elif path == b"/off":
                        led.value(0)
                    elif  == b"/toggle":
                        led.value(0 if led.value() else 1)

                    cl.sendall(html_page(led.value()))
            except Exception as e:
                # Print diagnostics and return 500
                try:
                    print("[HTTP] Error:", e)
                    try:
                        print("[HTTP] First line:", first)
                    except Exception:
                        pass
                except Exception:
                    pass
                try:
                    cl.sendall(b"HTTP/1.1 500 Internal Server Error\r\nConnection: close\r\n\r\n")
                except Exception:
                    pass
            finally:
                try:
                    cl.close()
                except Exception:
                    pass
    finally:
        try:
            s.close()
        except Exception:
            pass


if __name__ == "__main__":
    ip_addr = connect_wifi()
    serve_forever(ip_addr)
