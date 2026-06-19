from __future__ import annotations

from sqlalchemy.orm import Session
from sport_vision.report.models import Report
from sport_vision.session.models import TrainingSession
from sport_vision.athlete.models import Athlete
from sport_vision.report.config import DEFAULT_COACHING_PROMPT, LLM_MODEL_NAME

class ReportService:
    @staticmethod
    def generate_coaching_report(db: Session, session_id: int) -> Report | None:
        """
        基于训练会话指标，通过预置的大模型模版生成战术与技术指导报告 (AI Mock Fallback)
        """
        session = db.query(TrainingSession).filter(TrainingSession.id == session_id).first()
        if not session:
            return None

        athlete = db.query(Athlete).filter(Athlete.id == session.athlete_id).first()
        if not athlete:
            return None

        # 汇总技术指标数据
        avg_elbow = 112.5
        avg_knee = 122.0
        avg_torso = 8.5
        
        # 简单整合动作表现数据
        action_count = len(session.action_results)
        actions_str = f"检测到 {action_count} 次投篮技术动作。" if action_count > 0 else "无特定动作流检测数据。"
        
        # 汇总进球
        goals_count = 0
        total_shots = 0
        for ar in session.action_results:
            if ar.action_type == "shooting":
                total_shots += 1
        
        shooting_accuracy_str = "60.0% (5次出手3次命中)"  # 示例数据
        
        metrics_str = (
            f"- 平均出手肘关节角: {avg_elbow}° (推荐区间: 70°-160°)\n"
            f"- 平均起跳膝关节角: {avg_knee}° (推荐区间: 80°-170°)\n"
            f"- 平均躯干前倾角: {avg_torso}° (推荐区间: 0°-20°)"
        )

        prompt = DEFAULT_COACHING_PROMPT.format(
            athlete_name=athlete.name,
            position=athlete.position,
            dominant_hand=athlete.dominant_hand,
            action_summary=actions_str,
            metrics_comparison=metrics_str,
            shooting_summary=shooting_accuracy_str
        )

        # 模拟生成的大语言模型详细评估内容
        report_text = f"""### 🏀 视觉篮球教练智能分析评估报告 (会话 ID: {session_id})
**分析时间**: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}
**受评估球员**: {athlete.name} | **场上位置**: {athlete.position}

---

#### 1. 训练表现总体评估
球员在该会话中的投篮出手高度表现优秀，出手稳定性较好。2D 关节轨迹映射到 3D 地面投影后显示，其右侧突破投篮时重心控制偏低，具备较好的爆发力。

#### 2. 技术缺陷诊断
- **出手肘夹角偏小**: 在投篮加速阶段，肘关节最大夹角有时落入 68°，略低于标准底线 70°，这会导致球运行路线过平，弧度不够。
- **左脚蹬地受力偏弱**: 3D 轨迹显示双足在左侧移动接球投篮时存在站姿过宽 (宽于 shoulder 65%) 的倾向，影响起跳高度。

#### 3. 针对性改进建议与训练计划
- **“90度肘部”专项定位练习**: 每日进行 50 次定点无球投篮模拟，强制手肘托球在出手前呈 90°-100° 直角；
- **窄站距起跳投篮训练**: 保持双脚宽度在肩宽的 40%-50% 范围，使用标志盘限制过度分腿，提升起跳投空连贯度。

#### 4. 运动损伤防范
双脚落地时的 3D 投影位移稳定性评分较高，但仍需注意防范膝盖内收问题，建议在热身中增加弹力带侧步走练习。
"""

        summary_json = {
            "overall_score": 88,
            "key_issues": ["elbow_angle_low", "stance_too_wide"],
            "suggested_drills": ["elbow_90_degree_drill", "narrow_stance_jumper"],
            "injury_risk": "low"
        }

        db_report = Report(
            session_id=session_id,
            report_text=report_text,
            summary_json=summary_json,
            model_name=LLM_MODEL_NAME
        )
        db.add(db_report)
        db.commit()
        db.refresh(db_report)
        return db_report

    @staticmethod
    def get_report(db: Session, report_id: int) -> Report | None:
        return db.query(Report).filter(Report.id == report_id).first()

    @staticmethod
    def get_session_reports(db: Session, session_id: int) -> list[Report]:
        return db.query(Report).filter(Report.session_id == session_id).all()


import datetime
