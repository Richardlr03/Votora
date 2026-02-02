import os

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


class Config:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://root:password@127.0.0.1:3306/voting?charset=utf8mb4",
    )
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")

    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", MAIL_USERNAME)

    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {
            "ssl": {"ca": os.getenv("MYSQL_SSL_CA", "")}
            if os.getenv("MYSQL_SSL_CA")
            else {}
        }
    }
