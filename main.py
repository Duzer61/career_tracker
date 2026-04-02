import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.applications_routers import router as board_router
from app.api.auth_routers import router as auth_router
from app.api.user_routes import router as user_router
from app.db.redis import redis_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Connect to Redis
    await redis_client.connect()
    yield
    # Close Redis connection
    await redis_client.close()


app = FastAPI(lifespan=lifespan, title="Career tracker")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(board_router)


if __name__ == "__main__":
    self_filename = os.path.splitext(os.path.basename(__file__))[0]
    uvicorn.run(f"{self_filename}:app", host="127.0.0.1", port=8000, reload=True)
