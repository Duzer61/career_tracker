import os

import uvicorn
from fastapi import FastAPI

app = FastAPI(title="Career tracker")


@app.get("/")
def read_root():
    return {"message": "App started"}


if __name__ == "__main__":
    self_filename = os.path.splitext(os.path.basename(__file__))[0]
    uvicorn.run(f"{self_filename}:app", host="127.0.0.1", port=8000, reload=True)
