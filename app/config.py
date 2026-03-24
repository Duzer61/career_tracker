from dataclasses import dataclass

from environs import Env


@dataclass
class DatabaseConfig:
    db_url: str


@dataclass
class Config:
    db: DatabaseConfig
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXP_MINUTES: int
    REFRESH_TOKEN_EXP_DAYS: int
    DEFAULT_TOKEN_LIFETIME: int = 30  # minutes


def load_config() -> Config:
    env = Env()
    env.read_env()

    return Config(
        db=DatabaseConfig(
            db_url=f"postgresql+asyncpg://{env("POSTGRES_USER")}:{env("POSTGRES_PASSWORD")}"
            f"@{env("POSTGRES_HOST")}/{env("POSTGRES_DB")}"
        ),
        SECRET_KEY=env("SECRET_KEY"),
        ALGORITHM=env("ALGORITHM"),
        ACCESS_TOKEN_EXP_MINUTES=env("ACCESS_TOKEN_EXP_MINUTES"),
        REFRESH_TOKEN_EXP_DAYS=env("REFRESH_TOKEN_EXP_DAYS"),
    )


config = load_config()
