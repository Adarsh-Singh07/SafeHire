from app.db.base import Base
from app.db.session import engine
# Import all models to ensure they are registered with the Base metadata
from app.models import User, Company, JobCheck, SafetyLog

async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
