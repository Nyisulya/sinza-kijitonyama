import urllib.request

try:
    resp = urllib.request.urlopen("http://127.0.0.1:8000/", timeout=5)
    print(f"STATUS: {resp.status}")
    body = resp.read().decode("utf-8", errors="ignore")
    print(f"LENGTH: {len(body)} bytes")
    print("SERVER IKO ONLINE! Fungua http://127.0.0.1:8000/ kwenye browser yako.")
except Exception as e:
    print(f"IMESHINDWA: {e}")
