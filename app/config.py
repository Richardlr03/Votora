import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


class Config:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    _database_url = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://root:password@127.0.0.1:3306/voting?charset=utf8mb4",
    )
    if _database_url.startswith("mysql://"):
        _database_url = _database_url.replace("mysql://", "mysql+pymysql://", 1)
    SQLALCHEMY_DATABASE_URI = _database_url
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")

    RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")

    SUPPORT_NOTIFY_EMAIL = os.getenv("SUPPORT_NOTIFY_EMAIL", "")
    SUPPORT_FROM_EMAIL = os.getenv(
        "SUPPORT_FROM_EMAIL",
        "Votora Support <support@votora.me>",
    )
    DEV_ADMIN_USERNAMES = [
        item.strip()
        for item in os.getenv("DEV_ADMIN_USERNAMES", "").split(",")
        if item.strip()
    ]

    _mysql_connect_args = {
        "connect_timeout": int(os.getenv("MYSQL_CONNECT_TIMEOUT", "10")),
    }
    _mysql_ssl_ca = (os.getenv("MYSQL_SSL_CA") or "").strip()
    if _mysql_ssl_ca:
        _mysql_connect_args["ssl"] = {"ca": _mysql_ssl_ca}

    _is_mysql = _database_url.startswith("mysql")
    if _is_mysql:
        SQLALCHEMY_ENGINE_OPTIONS = {
            "pool_pre_ping": True,
            "pool_size": int(os.getenv("SQLALCHEMY_POOL_SIZE", "5")),
            "max_overflow": int(os.getenv("SQLALCHEMY_MAX_OVERFLOW", "5")),
            "pool_timeout": int(os.getenv("SQLALCHEMY_POOL_TIMEOUT", "30")),
            "pool_recycle": int(os.getenv("SQLALCHEMY_POOL_RECYCLE", "280")),
            "connect_args": _mysql_connect_args,
        }
    else:
        SQLALCHEMY_ENGINE_OPTIONS = {}
