import os
import threading

from bot import main as run_bot
from dashboard import app
from database import init_db

try:
    from waitress import serve
except ImportError:
    serve = None


def run_dashboard():
    port = int(os.getenv("PORT", "5050"))
    if serve:
        serve(app, host="0.0.0.0", port=port, threads=8)
    else:
        app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    init_db()
    thread = threading.Thread(target=run_dashboard, daemon=True)
    thread.start()
    print(f"Dashboard disponible en http://127.0.0.1:{os.getenv('PORT', '5050')}")
    run_bot()
