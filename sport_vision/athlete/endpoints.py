from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from sport_vision.db.database import get_db
from sport_vision.athlete.schemas import (
    AthleteCreate,
    AthleteUpdate,
    AthleteResponse,
    BodyHistoryCreate,
    BodyHistoryResponse,
    RecommendationRuleResponse
)
from sport_vision.athlete.services import AthleteService

router = APIRouter(prefix="/athletes", tags=["athletes"])

@router.post("", response_model=AthleteResponse, status_code=status.HTTP_201_CREATED)
def register_athlete(athlete: AthleteCreate, db: Session = Depends(get_db)):
    """注册新运动员档案"""
    return AthleteService.create_athlete(db, athlete)


@router.get("", response_model=list[AthleteResponse])
def list_athletes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """获取所有运动员列表"""
    return AthleteService.list_athletes(db, skip=skip, limit=limit)


@router.get("/{athlete_id}", response_model=AthleteResponse)
def get_athlete(athlete_id: int, db: Session = Depends(get_db)):
    """根据 ID 获取运动员详细档案"""
    db_athlete = AthleteService.get_athlete(db, athlete_id)
    if not db_athlete:
        raise HTTPException(status_code=404, detail="运动员未找到")
    return db_athlete


@router.put("/{athlete_id}", response_model=AthleteResponse)
def update_athlete(athlete_id: int, athlete_in: AthleteUpdate, db: Session = Depends(get_db)):
    """更新运动员属性"""
    db_athlete = AthleteService.update_athlete(db, athlete_id, athlete_in)
    if not db_athlete:
        raise HTTPException(status_code=404, detail="运动员未找到")
    return db_athlete


@router.delete("/{athlete_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_athlete(athlete_id: int, db: Session = Depends(get_db)):
    """删除指定运动员档案"""
    success = AthleteService.delete_athlete(db, athlete_id)
    if not success:
        raise HTTPException(status_code=404, detail="运动员未找到")
    return None


@router.post("/{athlete_id}/body-history", response_model=BodyHistoryResponse)
def log_body_history(athlete_id: int, body_in: BodyHistoryCreate, db: Session = Depends(get_db)):
    """为指定运动员追加身体变化记录"""
    db_body = AthleteService.add_body_history(db, athlete_id, body_in)
    if not db_body:
        raise HTTPException(status_code=404, detail="运动员未找到")
    return db_body


@router.get("/{athlete_id}/body-history/trends", response_model=list[BodyHistoryResponse])
def get_body_trends(athlete_id: int, db: Session = Depends(get_db)):
    """查询运动员身体状况的历史变动趋势（时间升序）"""
    return AthleteService.get_body_history_trends(db, athlete_id)


@router.get("/{athlete_id}/recommendations", response_model=list[RecommendationRuleResponse])
def get_athlete_recommendations(athlete_id: int, db: Session = Depends(get_db)):
    """依据当前运动员的年龄与场上位置，匹配获取合适的技术动作推荐物理指标范围"""
    db_athlete = AthleteService.get_athlete(db, athlete_id)
    if not db_athlete:
        raise HTTPException(status_code=404, detail="运动员未找到")
    
    age_group = "youth" if db_athlete.age < 18 else "adult"
    return AthleteService.get_recommendation_rules(db, age_group, db_athlete.position)
