import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.routes import router
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
app.include_router(router)


@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


if __name__ == "__main__":
    self_filename = os.path.splitext(os.path.basename(__file__))[0]
    uvicorn.run(f"{self_filename}:app", host="127.0.0.1", port=8000, reload=True)
