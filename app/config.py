from dataclasses import dataclass

from environs import Env


@dataclass
class DatabaseConfig:
    db_url: str


@dataclass
class Config:
    db: DatabaseConfig


def load_config() -> Config:
    env = Env()
    env.read_env()

    return Config(
        db=DatabaseConfig(
            db_url=f"postgresql+asyncpg://{env("POSTGRES_USER")}:{env("POSTGRES_PASSWORD")}"
            f"@{env("POSTGRES_HOST")}/{env("POSTGRES_DB")}"
        )
    )


config = load_config()
