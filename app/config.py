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
    TURNSTILE_SITE_KEY: str = ""
    TURNSTILE_SECRET_KEY: str = ""
    DEFAULT_TOKEN_LIFETIME: int = 30  # minutes


def load_config() -> Config:
    env = Env()
    env.read_env()

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
        TURNSTILE_SITE_KEY=env("TURNSTILE_SITE_KEY", default=""),
        TURNSTILE_SECRET_KEY=env("TURNSTILE_SECRET_KEY", default=""),
    )


config = load_config()
