from dataclasses import dataclass

from environs import Env


@dataclass
class DatabaseConfig:
    db_url: str


@dataclass
class RedisConfig:
    redis_url: str


@dataclass
class Config:
    db: DatabaseConfig
    redis: RedisConfig
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXP_MINUTES: int
    REFRESH_TOKEN_EXP_DAYS: int
    ENVIRON: str
    ONLY_ALLOWED_USERNAMES_MODE: bool
    ALLOWED_USERNAMES: list[str]
    IS_PROD: bool
    SMARTCAPTCHA_SITE_KEY: str
    SMARTCAPTCHA_SECRET_KEY: str
    SUPERADMIN_LOGIN: str = ""
    DEFAULT_TOKEN_LIFETIME: int = 30  # minutes
    MAX_LOGIN_ATTEMPTS: int = 10  # max attempts in time window
    WINDOW_LOGIN_ATTEMPTS: int = 300  # seconds
    AUTO_IGNORE_DAYS: int = 30  # days after which created applications are auto-ignored
    ADMIN_PAGE_SIZE: int = 20  # users per page in admin panel (1–100)
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5432"
    POSTGRES_USER: str = ""
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""
    BACKUP_DIR: str = "/backups"
    BACKUP_RETENTION_DAYS: int = 30  # backup files retention period in days


def get_bool(value: str | None) -> bool:
    if value is None:
        return False
    return value.lower() in ("true", "1", "yes", "y", "on")


def load_config() -> Config:
    env = Env()
    env.read_env()

    # Load allowed usernames
    allowed_usernames = [
        name.strip() for name in env("ALLOWED_USERNAMES", "").split(",") if name.strip()
    ]

    # PostgreSQL credentials — read once, reused for db_url and pg_dump
    pg_host = env("POSTGRES_HOST")
    pg_port = env("POSTGRES_PORT")
    pg_user = env("POSTGRES_USER")
    pg_password = env("POSTGRES_PASSWORD")
    pg_db = env("POSTGRES_DB")

    return Config(
        db=DatabaseConfig(
            db_url=f"postgresql+asyncpg://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_db}"
        ),
        POSTGRES_HOST=pg_host,
        POSTGRES_PORT=pg_port,
        POSTGRES_USER=pg_user,
        POSTGRES_PASSWORD=pg_password,
        POSTGRES_DB=pg_db,
        redis=RedisConfig(
            redis_url=f"redis://:{env("REDIS_PASSWORD")}@{env("REDIS_HOST")}"
            f":{env("REDIS_PORT")}/0"
        ),
        SECRET_KEY=env("SECRET_KEY"),
        ALGORITHM=env("ALGORITHM"),
        ACCESS_TOKEN_EXP_MINUTES=int(env("ACCESS_TOKEN_EXP_MINUTES")),
        REFRESH_TOKEN_EXP_DAYS=int(env("REFRESH_TOKEN_EXP_DAYS")),
        ENVIRON=env("ENVIRON"),
        ONLY_ALLOWED_USERNAMES_MODE=get_bool(env("ONLY_ALLOWED_USERNAMES_MODE", "on")),
        ALLOWED_USERNAMES=allowed_usernames,
        IS_PROD=env("ENVIRON") == "prod",
        SMARTCAPTCHA_SITE_KEY=env("SMARTCAPTCHA_SITE_KEY", ""),
        SMARTCAPTCHA_SECRET_KEY=env("SMARTCAPTCHA_SECRET_KEY", ""),
        SUPERADMIN_LOGIN=env("SUPERADMIN_LOGIN", ""),
    )


config = load_config()
