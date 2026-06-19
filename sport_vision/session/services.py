from __future__ import annotations

import os
import cv2
import datetime
from sqlalchemy.orm import Session
from typing import Any

from sport_vision.session.models import TrainingSession, MediaAsset, ActionResult, PerformanceMetric
from sport_vision.session.schemas import SessionCreate, SessionUpdate, PerformanceMetricCreate, ActionResultCreate
from sport_vision.session.config import RECORD_DIR, RECORD_CODEC, RECORD_FPS, RECORD_RESOLUTION

class VideoRecorder:
    """实时摄像头帧服务端录制器"""
    def __init__(self, session_id: int) -> None:
        self.session_id = session_id
        self.writer: cv2.VideoWriter | None = None
        self.file_path = os.path.join(RECORD_DIR, f"session_{session_id}_{int(datetime.datetime.utcnow().timestamp())}.mp4")

    def write_frame(self, frame_bgr: cv2.Mat) -> None:
        if not self.writer:
            # 自动适配视频大小
            h, w = frame_bgr.shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*RECORD_CODEC)
            self.writer = cv2.VideoWriter(self.file_path, fourcc, RECORD_FPS, (w, h))
        self.writer.write(frame_bgr)

    def stop_and_save(self, db: Session) -> MediaAsset:
        """停止录像并将生成的 MP4 关联写入 media_assets"""
        if self.writer:
            self.writer.release()
            self.writer = None
        
        # 探测视频时长与分辨率
        cap = cv2.VideoCapture(self.file_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or float(RECORD_FPS)
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = float(frame_count / fps) if fps > 0 else 0.0
        cap.release()

        db_asset = MediaAsset(
            session_id=self.session_id,
            file_path=self.file_path,
            source_type="record",
            fps=fps,
            resolution=f"{w}x{h}",
            duration=duration
        )
        db.add(db_asset)
        db.commit()
        db.refresh(db_asset)
        return db_asset


class SessionService:
    @staticmethod
    def create_session(db: Session, session_in: SessionCreate) -> TrainingSession:
        db_session = TrainingSession(
            athlete_id=session_in.athlete_id,
            session_type=session_in.session_type,
            source_type=session_in.source_type,
            notes=session_in.notes,
            calibration_data=session_in.calibration_data,
            status="created"
        )
        db.add(db_session)
        db.commit()
        db.refresh(db_session)
        return db_session

    @staticmethod
    def get_session(db: Session, session_id: int) -> TrainingSession | None:
        return db.query(TrainingSession).filter(TrainingSession.id == session_id).first()

    @staticmethod
    def list_sessions(db: Session, skip: int = 0, limit: int = 100) -> list[TrainingSession]:
        return db.query(TrainingSession).offset(skip).limit(limit).all()

    @staticmethod
    def update_session(db: Session, session_id: int, session_in: SessionUpdate) -> TrainingSession | None:
        db_session = db.query(TrainingSession).filter(TrainingSession.id == session_id).first()
        if not db_session:
            return None
        
        update_data = session_in.model_dump(exclude_unset=True)
        for key, val in update_data.items():
            setattr(db_session, key, val)
        
        db.commit()
        db.refresh(db_session)
        return db_session

    @staticmethod
    def save_media_asset(db: Session, session_id: int, file_path: str, source_type: str, fps: float, res: str, duration: float) -> MediaAsset:
        db_asset = MediaAsset(
            session_id=session_id,
            file_path=file_path,
            source_type=source_type,
            fps=fps,
            resolution=res,
            duration=duration
        )
        db.add(db_asset)
        db.commit()
        db.refresh(db_asset)
        return db_asset

    @staticmethod
    def add_action_result(db: Session, session_id: int, action_in: ActionResultCreate) -> ActionResult:
        db_action = ActionResult(
            session_id=session_id,
            action_type=action_in.action_type,
            start_frame=action_in.start_frame,
            end_frame=action_in.end_frame,
            confidence=action_in.confidence
        )
        db.add(db_action)
        db.commit()
        db.refresh(db_action)
        return db_action

    @staticmethod
    def save_performance_metrics(db: Session, session_id: int, metrics_in: PerformanceMetricCreate) -> PerformanceMetric:
        db_metric = PerformanceMetric(
            session_id=session_id,
            shot_angle=metrics_in.shot_angle,
            release_time=metrics_in.release_time,
            jump_height=metrics_in.jump_height,
            shot_accuracy=metrics_in.shot_accuracy,
            body_stability=metrics_in.body_stability,
            symmetry_score=metrics_in.symmetry_score
        )
        db.add(db_metric)
        db.commit()
        db.refresh(db_metric)
        return db_metric
