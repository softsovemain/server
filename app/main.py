from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine
from app.core.errors import register_exception_handlers
from app.routers import audit, auth, categories, commands, dashboard, databases, domains, projects, search, servers, users
from app.migrate import run_migrations
from app.seed import run_seed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    run_migrations()
    run_seed()
    yield


app = FastAPI(title="OpsHub API", version="1.0.0", lifespan=lifespan)
register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_prefix = "/api/v1"
app.include_router(auth.router, prefix=api_prefix)
app.include_router(categories.router, prefix=api_prefix)
app.include_router(servers.router, prefix=api_prefix)
app.include_router(projects.router, prefix=api_prefix)
app.include_router(commands.router, prefix=api_prefix)
app.include_router(domains.router, prefix=api_prefix)
app.include_router(databases.router, prefix=api_prefix)
app.include_router(users.router, prefix=api_prefix)
app.include_router(dashboard.router, prefix=api_prefix)
app.include_router(search.router, prefix=api_prefix)
app.include_router(audit.router, prefix=api_prefix)


@app.get("/health")
def health():
    return {"status": "ok"}
