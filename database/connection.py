"""
database/connection.py
======================
RR Intelligence Hub – Database Connection Layer
Supports PostgreSQL with automatic, reliable fallback to SQLite if PostgreSQL
is not currently active on the host machine.
"""

import os
import logging
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("database")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_DIR = PROJECT_ROOT / "database"
DB_DIR.mkdir(parents=True, exist_ok=True)
SQLITE_PATH = DB_DIR / "rr_intelligence.db"

Base = declarative_base()

def get_engine():
    """Create and return a resilient SQLAlchemy engine."""
    # Check if Postgres parameters are provided in environment
    db_user = os.getenv("DB_USER")
    db_pass = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "rr_intelligence_db")
    custom_url = os.getenv("DATABASE_URL")

    if custom_url:
        postgres_url = custom_url
    elif db_user and db_pass:
        postgres_url = f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    else:
        postgres_url = None

    if postgres_url:
        try:
            log.info("Attempting connection to PostgreSQL...")
            pg_engine = create_engine(
                postgres_url,
                pool_pre_ping=True,
                connect_args={"connect_timeout": 3}
            )
            with pg_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            log.info("Successfully connected to PostgreSQL database!")
            return pg_engine
        except Exception as e:
            log.warning(f"PostgreSQL connection unavailable ({e}). Falling back to local high-performance SQLite database.")

    # SQLite fallback
    sqlite_url = f"sqlite:///{SQLITE_PATH}"
    log.info(f"Using SQLite database engine at {SQLITE_PATH}")
    sqlite_engine = create_engine(
        sqlite_url,
        connect_args={"check_same_thread": False}
    )
    return sqlite_engine

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """FastAPI Dependency for database session management."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
