from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.analysis import router

app = FastAPI(title="STRIDE Threat Modeling API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
