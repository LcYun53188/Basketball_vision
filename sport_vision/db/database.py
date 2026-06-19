from __future__ import annotations

import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# 默认使用本地 SQLite 数据库，方便开箱即用；支持通过环境变量切换为 PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sport_vision.db")

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    # SQLite 专属配置，允许跨线程共享会话
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖注入会话生成器"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
