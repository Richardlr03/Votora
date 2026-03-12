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

    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", MAIL_USERNAME)

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "connect_args": {
            "ssl": {"ca": os.getenv("MYSQL_SSL_CA", "")}
            if os.getenv("MYSQL_SSL_CA")
            else {}
        }
    }
