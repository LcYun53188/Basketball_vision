from __future__ import annotations

import datetime
from typing import Optional
from pydantic import BaseModel, Field

# --- 身体状况指标 ---
class BodyHistoryBase(BaseModel):
    height: float = Field(..., description="身高 (cm)", gt=0)
    weight: float = Field(..., description="体重 (kg)", gt=0)
    wingspan: float = Field(..., description="臂展 (cm)", gt=0)
    body_fat: float = Field(..., description="体脂率 (%)", ge=0, le=100)

class BodyHistoryCreate(BodyHistoryBase):
    pass

class BodyHistoryResponse(BodyHistoryBase):
    id: int
    athlete_id: int
    measurement_date: datetime.datetime

    class Config:
        from_attributes = True

# --- 运动员主档案 ---
class AthleteBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    gender: str = Field(..., pattern="^(male|female|other)$")
    age: int = Field(..., ge=1, le=120)
    position: str = Field(..., pattern="^(guard|forward|center)$")
    dominant_hand: str = Field(..., pattern="^(left|right)$")

class AthleteCreate(AthleteBase):
    # 允许在创建时同时传入初始身体指标
    initial_body: Optional[BodyHistoryCreate] = None

class AthleteUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    gender: Optional[str] = Field(None, pattern="^(male|female|other)$")
    age: Optional[int] = Field(None, ge=1, le=120)
    position: Optional[str] = Field(None, pattern="^(guard|forward|center)$")
    dominant_hand: Optional[str] = Field(None, pattern="^(left|right)$")

class AthleteResponse(AthleteBase):
    id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime
    body_histories: list[BodyHistoryResponse] = []

    class Config:
        from_attributes = True

# --- 推荐规则配置 ---
class RecommendationRuleBase(BaseModel):
    rule_name: str
    age_group: str = Field(..., pattern="^(youth|adult)$")
    position: str = Field(..., pattern="^(guard|forward_center)$")
    metric_name: str
    min_value: float
    max_value: float
    target_value: float

class RecommendationRuleCreate(RecommendationRuleBase):
    pass

class RecommendationRuleResponse(RecommendationRuleBase):
    id: int

    class Config:
        from_attributes = True
