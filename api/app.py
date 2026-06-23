"""FastAPI JSON API for the Founder OS dashboard."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import config
from api.routers import spaces, assets, state, crud, cognition


def create_app() -> FastAPI:
    app = FastAPI(title="Founder OS API", version="1.0.0")
    origins = [o.strip() for o in config.web_origin.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(state.router, prefix="/api")
    app.include_router(spaces.router, prefix="/api")
    app.include_router(assets.router, prefix="/api")
    app.include_router(crud.router, prefix="/api")
    app.include_router(cognition.router, prefix="/api")
    return app


app = create_app()
