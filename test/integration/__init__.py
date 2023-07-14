import os

from dotenv import load_dotenv
load_dotenv()
HOST = os.environ.get("JELLYFIN_URI") or "http://jellyfin:8096"
USERNAME = os.environ.get("JELLYFIN_USERNAME")
PASSWORD = os.environ.get("JELLYFIN_PASSWORD")