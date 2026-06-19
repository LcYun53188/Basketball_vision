from __future__ import annotations

from sqlalchemy.orm import Session
from sport_vision.athlete.models import Athlete, AthleteBodyHistory, RecommendationRule
from sport_vision.athlete.schemas import AthleteCreate, AthleteUpdate, BodyHistoryCreate
from sport_vision.athlete.config import DEFAULT_RECOMMENDATION_RULES

class AthleteService:
    @staticmethod
    def create_athlete(db: Session, athlete_in: AthleteCreate) -> Athlete:
        """注册运动员，并可同步添加初次身体测量档案"""
        db_athlete = Athlete(
            name=athlete_in.name,
            gender=athlete_in.gender,
            age=athlete_in.age,
            position=athlete_in.position,
            dominant_hand=athlete_in.dominant_hand
        )
        db.add(db_athlete)
        db.flush()  # 获取自增 ID

        if athlete_in.initial_body:
            body_history = AthleteBodyHistory(
                athlete_id=db_athlete.id,
                height=athlete_in.initial_body.height,
                weight=athlete_in.initial_body.weight,
                wingspan=athlete_in.initial_body.wingspan,
                body_fat=athlete_in.initial_body.body_fat
            )
            db.add(body_history)
        
        db.commit()
        db.refresh(db_athlete)
        return db_athlete

    @staticmethod
    def get_athlete(db: Session, athlete_id: int) -> Athlete | None:
        return db.query(Athlete).filter(Athlete.id == athlete_id).first()

    @staticmethod
    def list_athletes(db: Session, skip: int = 0, limit: int = 100) -> list[Athlete]:
        return db.query(Athlete).offset(skip).limit(limit).all()

    @staticmethod
    def update_athlete(db: Session, athlete_id: int, athlete_in: AthleteUpdate) -> Athlete | None:
        db_athlete = db.query(Athlete).filter(Athlete.id == athlete_id).first()
        if not db_athlete:
            return None
        
        update_data = athlete_in.model_dump(exclude_unset=True)
        for key, val in update_data.items():
            setattr(db_athlete, key, val)
        
        db.commit()
        db.refresh(db_athlete)
        return db_athlete

    @staticmethod
    def delete_athlete(db: Session, athlete_id: int) -> bool:
        db_athlete = db.query(Athlete).filter(Athlete.id == athlete_id).first()
        if not db_athlete:
            return False
        db.delete(db_athlete)
        db.commit()
        return True

    @staticmethod
    def add_body_history(db: Session, athlete_id: int, body_in: BodyHistoryCreate) -> AthleteBodyHistory | None:
        """追加运动员身体历史记录"""
        db_athlete = db.query(Athlete).filter(Athlete.id == athlete_id).first()
        if not db_athlete:
            return None
        
        db_body = AthleteBodyHistory(
            athlete_id=athlete_id,
            height=body_in.height,
            weight=body_in.weight,
            wingspan=body_in.wingspan,
            body_fat=body_in.body_fat
        )
        db.add(db_body)
        db.commit()
        db.refresh(db_body)
        return db_body

    @staticmethod
    def get_body_history_trends(db: Session, athlete_id: int) -> list[AthleteBodyHistory]:
        """获取身体指标随时间变化历史趋势"""
        return (
            db.query(AthleteBodyHistory)
            .filter(AthleteBodyHistory.athlete_id == athlete_id)
            .order_by(AthleteBodyHistory.measurement_date.asc())
            .all()
        )

    @staticmethod
    def ensure_default_rules(db: Session) -> None:
        """在没有规则配置时，自动初始化默认推荐区间配置库"""
        if db.query(RecommendationRule).count() > 0:
            return

        rules_to_create = []
        for age_grp, position_data in DEFAULT_RECOMMENDATION_RULES.items():
            for pos_name, metrics in position_data.items():
                for m_name, val_range in metrics.items():
                    rule = RecommendationRule(
                        rule_name=f"默认 {age_grp} {pos_name} {m_name} 标准区间",
                        age_group=age_grp,
                        position=pos_name,
                        metric_name=m_name,
                        min_value=val_range["min"],
                        max_value=val_range["max"],
                        target_value=val_range["target"]
                    )
                    rules_to_create.append(rule)
        
        db.bulk_save_objects(rules_to_create)
        db.commit()

    @staticmethod
    def get_recommendation_rules(db: Session, age_group: str, position: str) -> list[RecommendationRule]:
        """依据年龄段和位置，查询匹配的评估技术指标阈值"""
        # 统一映射 position: guard -> guard, forward/center -> forward_center
        pos_mapped = "guard" if position == "guard" else "forward_center"
        age_mapped = "youth" if age_group == "youth" else "adult"
        
        # 确保默认规则已加载
        AthleteService.ensure_default_rules(db)

        return (
            db.query(RecommendationRule)
            .filter(
                RecommendationRule.age_group == age_mapped,
                RecommendationRule.position == pos_mapped
            )
            .all()
        )
