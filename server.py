from pathlib import Path
import uvicorn

# Локальный HTTPS: сертификаты создаются командой mkcert (см. README)
CERTS_DIR = Path(__file__).parent / "certs"
CERT_FILE = CERTS_DIR / "localhost.pem"
KEY_FILE = CERTS_DIR / "localhost-key.pem"

if __name__ == "__main__":
    ssl_args = {}
    if CERT_FILE.exists() and KEY_FILE.exists():
        ssl_args = {"ssl_certfile": str(CERT_FILE), "ssl_keyfile": str(KEY_FILE)}
        print("[HTTPS] https://localhost:8000/docs")
    else:
        print("[HTTP] Сертификатов в certs/ нет — запуск без HTTPS: http://127.0.0.1:8000/docs")

    uvicorn.run("task_app.main:app", host="127.0.0.1", port=8000, reload=True, **ssl_args)
