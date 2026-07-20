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
    ADMIN_PAGE_SIZE: int = 2  # users per page in admin panel (1–100)


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

    return Config(
        db=DatabaseConfig(
            db_url=f"postgresql+asyncpg://{env("POSTGRES_USER")}:{env("POSTGRES_PASSWORD")}"
            f"@{env("POSTGRES_HOST")}:{env("POSTGRES_PORT")}/{env("POSTGRES_DB")}"
        ),
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
