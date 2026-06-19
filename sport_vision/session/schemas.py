from __future__ import annotations

import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field

# --- 媒体资源 ---
class MediaAssetResponse(BaseModel):
    id: int
    session_id: int
    file_path: str
    source_type: str
    fps: Optional[float] = None
    resolution: Optional[str] = None
    duration: Optional[float] = None

    class Config:
        from_attributes = True

# --- 物理动作指标 ---
class PerformanceMetricBase(BaseModel):
    shot_angle: Optional[float] = None
    release_time: Optional[float] = None
    jump_height: Optional[float] = None
    shot_accuracy: Optional[float] = None
    body_stability: Optional[float] = None
    symmetry_score: Optional[float] = None

class PerformanceMetricCreate(PerformanceMetricBase):
    pass

class PerformanceMetricResponse(PerformanceMetricBase):
    id: int
    session_id: int

    class Config:
        from_attributes = True

# --- 动作切片结果 ---
class ActionResultBase(BaseModel):
    action_type: str
    start_frame: int
    end_frame: int
    confidence: float

class ActionResultCreate(ActionResultBase):
    pass

class ActionResultResponse(ActionResultBase):
    id: int
    session_id: int

    class Config:
        from_attributes = True

# --- 会话档案 ---
class SessionBase(BaseModel):
    athlete_id: int
    session_type: str = "shooting_drill"
    source_type: str = Field(..., pattern="^(video|camera)$")
    calibration_data: Optional[dict[str, Any]] = None
    notes: Optional[str] = None

class SessionCreate(SessionBase):
    pass

class SessionUpdate(BaseModel):
    status: Optional[str] = None
    end_time: Optional[datetime.datetime] = None
    notes: Optional[str] = None
    calibration_data: Optional[dict[str, Any]] = None

class SessionResponse(SessionBase):
    id: int
    status: str
    start_time: datetime.datetime
    end_time: Optional[datetime.datetime] = None
    media_assets: list[MediaAssetResponse] = []
    action_results: list[ActionResultResponse] = []
    performance_metrics: list[PerformanceMetricResponse] = []

    class Config:
        from_attributes = True

# --- WebSocket 传输协议 Schema ---
class WebSocketFrameOut(BaseModel):
    frame_index: int
    timestamp_ms: float
    keypoints: list[dict[str, Any]]
    feet_pixel: Optional[list[float]] = None  # [x, y] 像素点
    feet_world_3d: Optional[list[float]] = None  # [X, Y, Z=0] 三维实境投影坐标 (米)
    skeleton_world_3d: Optional[dict[str, list[float]]] = None  # 3D 空间投射关节点坐标
    action_type: str = "idle"
    # 标准对比结果 (若开启 compare_with_reference=True)
    comparisons: Optional[list[dict[str, Any]]] = None
    # 进球判定事件
    goal_event: Optional[dict[str, Any]] = None
    # 跟踪结果
    ball_bbox: Optional[list[int]] = None
    hoop_bbox: Optional[list[int]] = None
    ball_world_3d: Optional[list[float]] = None
    hoop_world_3d: Optional[list[float]] = None
    detector_meta: Optional[dict[str, Any]] = None
    frame: Optional[str] = None
