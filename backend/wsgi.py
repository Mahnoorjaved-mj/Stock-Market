"""Production WSGI entry point.

Run with Waitress on Windows:
    waitress-serve --listen=0.0.0.0:5000 --threads=8 backend.wsgi:app

Or directly (this picks waitress on Windows, gunicorn elsewhere via the Dockerfile):
    python -m backend.wsgi
"""
import os
import sys

# Ensure `backend/` is on sys.path when run as a module from project root.
_THIS_DIR = os.path.abspath(os.path.dirname(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from app import app  # noqa: E402

if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "5000"))
    threads = int(os.environ.get("THREADS", "8"))
    if sys.platform == "win32":
        from waitress import serve
        print(f"Starting Waitress on http://{host}:{port} (threads={threads})")
        serve(app, host=host, port=port, threads=threads)
    else:
        # gunicorn is invoked from the Docker CMD; fallback to waitress here too.
        from waitress import serve
        serve(app, host=host, port=port, threads=threads)
