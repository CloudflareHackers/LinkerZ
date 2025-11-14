# This file is a part of TG
# Coding : Jyothis Jayanth [@EverythingSuckz]

from os import environ
from dotenv import load_dotenv

load_dotenv()


class Var(object):
    MULTI_CLIENT = False
    API_ID = int(environ.get("API_ID"))
    API_HASH = str(environ.get("API_HASH"))
    BOT_TOKEN = str(environ.get("BOT_TOKEN"))
    SLEEP_THRESHOLD = int(environ.get("SLEEP_THRESHOLD", "60"))  # 1 minute
    WORKERS = int(environ.get("WORKERS", "3"))  # Reduced from 6 to 3 for memory optimization
    BIN_CHANNEL = int(
        environ.get("BIN_CHANNEL", None)
    )  # you NEED to use a CHANNEL when you're using MULTI_CLIENT
    BIN_CHANNEL_WITHOUT_MINUS = int(
        environ.get("BIN_CHANNEL_WITHOUT_MINUS", None)
    )  # you NEED to use a CHANNEL when you're using MULTI_CLIENT
    PORT = int(environ.get("PORT", 80))
    BIND_ADDRESS = str(environ.get("WEB_SERVER_BIND_ADDRESS", "0.0.0.0"))
    PING_INTERVAL = int(environ.get("PING_INTERVAL", "1200"))  # 20 minutes
    DATABASE_URL = str(environ.get("DATABASE_URL", ""))  # PostgreSQL database URL
    HAS_SSL = environ.get("HAS_SSL", False)
    HAS_SSL = True if str(HAS_SSL).lower() == "true" else False
    NO_PORT = environ.get("NO_PORT", False)
    NO_PORT = True if str(NO_PORT).lower() == "true" else False
    if "DYNO" in environ:
        ON_HEROKU = True
        APP_NAME = str(environ.get("APP_NAME"))
    else:
        ON_HEROKU = False
    FQDN = (
        str(environ.get("FQDN", BIND_ADDRESS))
        if not ON_HEROKU or environ.get("FQDN")
        else APP_NAME + ".herokuapp.com"
    )
    if ON_HEROKU:
        URL = f"https://{FQDN}/"
    else:
        URL = "http{}://{}{}/".format(
            "s" if HAS_SSL else "", FQDN, ""
        )
    # Secret key for download link integrity (generate one if not set)
    DOWNLOAD_SECRET_KEY = str(environ.get("DOWNLOAD_SECRET_KEY", "change-this-secret-key-in-production"))
    
    # R2 Storage Configuration
    R2_Domain = str(environ.get("R2_Domain", "tga-hd.api.hashhackers.com"))
    R2_Folder = str(environ.get("R2_Folder", "linkerz"))
    R2_Public = str(environ.get("R2_Public", "tg-files-identifier.hashhackers.com"))
