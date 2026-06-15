import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.admin_routes import router as admin_router
from app.api.applications_routers import router as board_router
from app.api.auth_routers import router as auth_router
from app.api.user_routes import router as user_router
from app.config import config as cf
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


app = FastAPI(
    lifespan=lifespan,
    title="Career tracker",
    docs_url=None if cf.IS_PROD else "/docs",
    redoc_url=None if cf.IS_PROD else "/redoc",
    openapi_url=None if cf.IS_PROD else "/openapi.json",
)


class NoCacheHTMLMiddleware(BaseHTTPMiddleware):
    """Disable browser caching for HTML responses to prevent stale page issues."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        content_type = response.headers.get("content-type", "")
        if "text/html" in content_type:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response


app.add_middleware(NoCacheHTMLMiddleware)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return templates.TemplateResponse(
        name="404.html", context={"request": request}, request=request, status_code=404
    )


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(
        name="index.html",
        context={
            "request": request,
            "smartcaptcha_site_key": cf.SMARTCAPTCHA_SITE_KEY,
        },
        request=request,
    )


app.include_router(auth_router)
app.include_router(user_router)
app.include_router(board_router)
app.include_router(admin_router)


if __name__ == "__main__":
    # Получаем хост и порт из переменных окружения или используем значения по умолчанию
    host = os.getenv("HOST", "0.0.0.0")  # Важно: в Docker нужно слушать 0.0.0.0
    port = int(os.getenv("PORT", "8000"))
    is_dev = os.getenv("ENVIRON", "dev") == "dev"

    uvicorn.run("main:app", host=host, port=port, reload=is_dev)
