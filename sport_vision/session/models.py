from __future__ import annotations

import datetime
from sqlalchemy import Integer, String, Float, ForeignKey, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sport_vision.db.database import Base

class TrainingSession(Base):
    """训练会话表，绑定每一次视频分析或实时检测记录"""
    __tablename__ = "training_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    athlete_id: Mapped[int] = mapped_column(Integer, ForeignKey("athletes.id", ondelete="CASCADE"), nullable=False)
    session_type: Mapped[str] = mapped_column(String(30), default="shooting_drill")  # e.g., shooting_drill
    source_type: Mapped[str] = mapped_column(String(20))  # e.g., video, camera
    status: Mapped[str] = mapped_column(String(20), default="created")  # created, processing, completed, failed
    calibration_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # 该会话所关联的 H 标定数据
    start_time: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    end_time: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # 关联关系
    athlete: Mapped[Athlete] = relationship("Athlete", back_populates="training_sessions")
    media_assets: Mapped[list[MediaAsset]] = relationship(
        "MediaAsset", back_populates="session", cascade="all, delete-orphan"
    )
    action_results: Mapped[list[ActionResult]] = relationship(
        "ActionResult", back_populates="session", cascade="all, delete-orphan"
    )
    performance_metrics: Mapped[list[PerformanceMetric]] = relationship(
        "PerformanceMetric", back_populates="session", cascade="all, delete-orphan"
    )
    reports: Mapped[list[Report]] = relationship(
        "Report", back_populates="session", cascade="all, delete-orphan"
    )


class MediaAsset(Base):
    """会话关联的视频媒体资源"""
    __tablename__ = "media_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("training_sessions.id", ondelete="CASCADE"), nullable=False)
    file_path: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(20))  # upload, record
    fps: Mapped[float | None] = mapped_column(Float, nullable=True)
    resolution: Mapped[str | None] = mapped_column(String(20), nullable=True)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)

    session: Mapped[TrainingSession] = relationship("TrainingSession", back_populates="media_assets")


class ActionResult(Base):
    """动作识别片段及分类置信度"""
    __tablename__ = "action_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("training_sessions.id", ondelete="CASCADE"), nullable=False)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    start_frame: Mapped[int] = mapped_column(Integer, nullable=False)
    end_frame: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)

    session: Mapped[TrainingSession] = relationship("TrainingSession", back_populates="action_results")


class PerformanceMetric(Base):
    """会话中识别的技术与运动表现细分物理指标"""
    __tablename__ = "performance_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("training_sessions.id", ondelete="CASCADE"), nullable=False)
    shot_angle: Mapped[float | None] = mapped_column(Float, nullable=True)       # 出手角度
    release_time: Mapped[float | None] = mapped_column(Float, nullable=True)     # 出手时间 (s)
    jump_height: Mapped[float | None] = mapped_column(Float, nullable=True)      # 起跳高度 (m)
    shot_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)    # 命中率 (%)
    body_stability: Mapped[float | None] = mapped_column(Float, nullable=True)   # 身体稳定度
    symmetry_score: Mapped[float | None] = mapped_column(Float, nullable=True)   # 动作对称得分

    session: Mapped[TrainingSession] = relationship("TrainingSession", back_populates="performance_metrics")


# 循环依赖处理导入
from sport_vision.athlete.models import Athlete
from sport_vision.report.models import Report
