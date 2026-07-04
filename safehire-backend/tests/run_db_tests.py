import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.db.base import Base
from app.models.user import User
from app.models.company import Company
from app.models.job_check import JobCheck
from app.models.safety_log import SafetyLog
from datetime import date

# Temporary in-memory database for testing database integrity
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

async def main():
    print("Initializing test database...")
    engine = create_async_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    
    # Create all database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created successfully.")
        
    SessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with SessionLocal() as session:
        # Test User Creation
        print("Testing User model creation...")
        user = User(email="seeker@offershield.com", hashed_password="hashed_pass")
        session.add(user)
        await session.commit()
        assert user.id is not None
        assert user.email == "seeker@offershield.com"
        print("User model verified successfully.")
        
        # Test Company Creation
        print("Testing Company model creation...")
        company = Company(
            name="Zenlyte Solutions Pvt Ltd",
            normalized_name="zenlyte solutions",
            cin="U72900KA2020PTC134567",
            registration_status="Active",
            incorporation_date=date(2020, 5, 20)
        )
        session.add(company)
        await session.commit()
        assert company.id is not None
        assert company.normalized_name == "zenlyte solutions"
        print("Company model verified successfully.")
        
        # Test JobCheck Creation
        print("Testing JobCheck model and relationship...")
        job_check = JobCheck(
            user_id=user.id,
            title="Software Developer",
            company_name="Zenlyte Solutions Pvt Ltd",
            raw_text="Job description text...",
            composite_score=85,
            risk_level="Low"
        )
        session.add(job_check)
        await session.commit()
        assert job_check.id is not None
        assert job_check.user_id == user.id
        print("JobCheck model verified successfully.")
        
        # Test SafetyLog Creation
        print("Testing SafetyLog model...")
        safety_log = SafetyLog(
            job_check_id=job_check.id,
            resulting_score=85
        )
        session.add(safety_log)
        await session.commit()
        assert safety_log.id is not None
        assert safety_log.job_check_id == job_check.id
        print("SafetyLog model verified successfully.")
        
        # Verify relationship lazy loading works
        await session.refresh(user)
        assert len(user.job_checks) == 1
        assert user.job_checks[0].title == "Software Developer"
        print("Model relationships verified successfully.")
        
    await engine.dispose()
    print("All database schema tests completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
