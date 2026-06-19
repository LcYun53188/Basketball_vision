from __future__ import annotations

import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from sport_vision.db.database import engine
from sport_vision.db import base  # 导入以加载所有 metadata
from sport_vision.athlete.endpoints import router as athlete_router
from sport_vision.session.endpoints import router as session_router
from sport_vision.report.endpoints import router as report_router

# 1. 自动建表（SQLite 模式开箱即用）
base.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="视觉篮球教练智能分析系统",
    description="高解耦、多模块集成的篮球运动员体测、视频分析及 3D 轨迹投影系统接口",
    version="1.0.0"
)

# 2. 跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. 挂载领域路由 API
app.include_router(athlete_router, prefix="/api/v1")
app.include_router(session_router, prefix="/api/v1")
app.include_router(report_router, prefix="/api/v1")

# 4. 托管 Web UI 静态资源
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)

# 根路由直接返回 index.html
@app.get("/")
def read_root():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "篮球教练系统已启动，但未检测到前端 UI 页面，请确认 static 文件夹已构建。"}

app.mount("/static", StaticFiles(directory=static_dir), name="static")
