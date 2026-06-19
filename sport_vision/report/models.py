from __future__ import annotations

import datetime
from sqlalchemy import Integer, String, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sport_vision.db.database import Base

class Report(Base):
    """大模型自动生成的训练建议与总结报告"""
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("training_sessions.id", ondelete="CASCADE"), nullable=False)
    report_text: Mapped[str] = mapped_column(Text, nullable=False)  # AI 建议正文
    summary_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # 结构化总结
    model_name: Mapped[str] = mapped_column(String(50), default="gemini-3.5-flash")
    generated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    session: Mapped[TrainingSession] = relationship("TrainingSession", back_populates="reports")


from sport_vision.session.models import TrainingSession
