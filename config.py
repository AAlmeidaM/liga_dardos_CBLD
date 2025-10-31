import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change_me")
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")
    TIMEZONE = os.getenv("TIMEZONE", "Europe/Madrid")
    NO_SHOW_WIN_POINTS = int(os.getenv("NO_SHOW_WIN_POINTS", "3"))
    PORT = int(os.getenv("PORT", "5000"))
