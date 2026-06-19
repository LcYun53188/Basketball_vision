from __future__ import annotations

import datetime
from sqlalchemy import Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sport_vision.db.database import Base

class Athlete(Base):
    """运动员档案主表"""
    __tablename__ = "athletes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    gender: Mapped[str] = mapped_column(String(10), nullable=False)  # e.g., male, female
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[str] = mapped_column(String(30), nullable=False)  # e.g., guard, forward, center
    dominant_hand: Mapped[str] = mapped_column(String(10), nullable=False)  # e.g., left, right
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )

    # 关联关系
    body_histories: Mapped[list[AthleteBodyHistory]] = relationship(
        "AthleteBodyHistory", back_populates="athlete", cascade="all, delete-orphan"
    )
    training_sessions: Mapped[list[TrainingSession]] = relationship(
        "TrainingSession", back_populates="athlete", cascade="all, delete"
    )


class AthleteBodyHistory(Base):
    """身体指标变更历史表"""
    __tablename__ = "athlete_body_histories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    athlete_id: Mapped[int] = mapped_column(Integer, ForeignKey("athletes.id", ondelete="CASCADE"), nullable=False)
    height: Mapped[float] = mapped_column(Float, nullable=False)  # 身高 (cm)
    weight: Mapped[float] = mapped_column(Float, nullable=False)  # 体重 (kg)
    wingspan: Mapped[float] = mapped_column(Float, nullable=False)  # 臂展 (cm)
    body_fat: Mapped[float] = mapped_column(Float, nullable=False)  # 体脂率 (%)
    measurement_date: Mapped[datetime.date] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )

    athlete: Mapped[Athlete] = relationship("Athlete", back_populates="body_histories")


class RecommendationRule(Base):
    """不同维度技术指标的合理/推荐阈值范围表"""
    __tablename__ = "recommendation_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    rule_name: Mapped[str] = mapped_column(String(100), nullable=False)
    age_group: Mapped[str] = mapped_column(String(20), nullable=False)  # youth, adult
    position: Mapped[str] = mapped_column(String(30), nullable=False)  # guard, forward_center
    metric_name: Mapped[str] = mapped_column(String(50), nullable=False)  # elbow_angle_deg, etc.
    min_value: Mapped[float] = mapped_column(Float, nullable=False)
    max_value: Mapped[float] = mapped_column(Float, nullable=False)
    target_value: Mapped[float] = mapped_column(Float, nullable=False)


# 延迟导入以解决循环依赖，因为 TrainingSession 位于 session.models 中
from sport_vision.session.models import TrainingSession
