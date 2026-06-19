from __future__ import annotations

# 导入 Base 声明
from sport_vision.db.database import Base

# 导入所有模块的 models，确保 metadata 能够检测并创建它们
from sport_vision.athlete.models import Athlete, AthleteBodyHistory, RecommendationRule
from sport_vision.session.models import TrainingSession, MediaAsset, ActionResult, PerformanceMetric
from sport_vision.report.models import Report
