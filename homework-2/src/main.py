from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.db.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Customer Support System",
    description="Intelligent customer support ticket management API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from src.routers import tickets, import_router, classify  # noqa: E402

app.include_router(tickets.router, prefix="", tags=["tickets"])
app.include_router(import_router.router, prefix="", tags=["import"])
app.include_router(classify.router, prefix="", tags=["classify"])


@app.get("/")
async def root():
    return {"status": "ok", "service": "Customer Support System"}
