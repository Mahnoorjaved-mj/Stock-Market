"""Root entrypoint for StockSense FastAPI application.
Allows running the service from repository root or subfolder seamlessly.
"""
import importlib.util
import os
import sys

_SERVER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server")
if _SERVER_DIR not in sys.path:
    sys.path.insert(0, _SERVER_DIR)

# Load server/main.py without circular import conflicts
_spec = importlib.util.spec_from_file_location("server_app", os.path.join(_SERVER_DIR, "main.py"))
_module = importlib.util.module_from_spec(_spec)
sys.modules["server_app"] = _module
_spec.loader.exec_module(_module)
app = _module.app

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port)
