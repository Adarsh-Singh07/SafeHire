from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

# Create async database engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

# Async session maker
SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Dependency to get db session in FastAPI endpoints
async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
            # Commit any pending changes at end of request
            await session.commit()
        except Exception as exc:
            # Always rollback on any error so the session is clean
            try:
                await session.rollback()
            except Exception:
                pass
            raise exc
        finally:
            await session.close()
