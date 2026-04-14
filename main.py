import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.applications_routers import router as board_router
from app.api.auth_routers import router as auth_router
from app.api.user_routes import router as user_router
from app.db.database import check_db_connection, engine
from app.db.redis import redis_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Connect to Redis
    await redis_client.connect()
    # Check PostgreSQL connection
    await check_db_connection()
    yield
    # Close Redis connection
    await redis_client.close()
    # Close PostgreSQL connection
    await engine.dispose()
    print("🔌 Соединение с PostgreSQL закрыто")


app = FastAPI(lifespan=lifespan, title="Career tracker")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(
        name="index.html", context={"request": request}, request=request
    )


app.include_router(auth_router)
app.include_router(user_router)
app.include_router(board_router)


if __name__ == "__main__":
    # Получаем хост и порт из переменных окружения или используем значения по умолчанию
    host = os.getenv("HOST", "0.0.0.0")  # Важно: в Docker нужно слушать 0.0.0.0
    port = int(os.getenv("PORT", "8000"))
    is_dev = os.getenv("ENVIRON", "dev") == "dev"

    uvicorn.run("main:app", host=host, port=port, reload=is_dev)
