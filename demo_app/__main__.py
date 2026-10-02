"""Execução standalone: python -m demo_app"""
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

from demo_app.app import create_app

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

username, password = os.getenv("TEST_USERNAME"), os.getenv("TEST_PASSWORD")
if not username or not password:
    sys.exit("Defina TEST_USERNAME e TEST_PASSWORD (veja .env.example).")

base = urlparse(os.getenv("BASE_URL", "http://127.0.0.1:5055"))
create_app(username, password).run(host=base.hostname or "127.0.0.1", port=base.port or 5055)
