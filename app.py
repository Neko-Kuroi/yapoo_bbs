from fastapi import FastAPI
from contextlib import asynccontextmanager

# 静的ファイルをマウントするために
from fastapi.staticfiles import StaticFiles

from init_db import init_db
import index
import webhook
import thread
import post
import search

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(lifespan=lifespan)

# 静的ファイルをマウント
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(index.router)
app.include_router(webhook.router)
app.include_router(thread.router)
app.include_router(post.router)
app.include_router(search.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
    
