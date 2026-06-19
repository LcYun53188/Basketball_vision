from __future__ import annotations

import base64
import os
import shutil
import cv2
import numpy as np
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Any

from sport_vision.db.database import get_db
from sport_vision.session.schemas import (
    SessionCreate,
    SessionUpdate,
    SessionResponse,
    MediaAssetResponse,
    WebSocketFrameOut
)
from sport_vision.session.services import SessionService, VideoRecorder
from sport_vision.session.config import UPLOAD_DIR
from sport_vision.vision.pose.pose_processor import PoseProcessor
from sport_vision.vision.action.action_detector import ActionDetector
from sport_vision.vision.calibration.calibration_tool import project_point_to_court
from sport_vision.vision.ball.ball_detector import BallDetector
from sport_vision.vision.ball.ball_detector import project_bbox_to_court
from sport_vision.vision.ball.geometry_3d import estimate_ball_world_from_bbox
from sport_vision.vision.goal.goal_detector import GoalDetector
from sport_vision.tasks.video_tasks import analyze_video_offline_background

router = APIRouter(prefix="/sessions", tags=["sessions"])

@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_training_session(session_in: SessionCreate, db: Session = Depends(get_db)):
    """创建训练会话"""
    return SessionService.create_session(db, session_in)


@router.get("", response_model=list[SessionResponse])
def list_sessions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """获取所有训练会话列表"""
    return SessionService.list_sessions(db, skip=skip, limit=limit)


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(session_id: int, db: Session = Depends(get_db)):
    """获取指定训练会话详情"""
    db_session = SessionService.get_session(db, session_id)
    if not db_session:
        raise HTTPException(status_code=404, detail="会话未找到")
    return db_session


@router.put("/{session_id}", response_model=SessionResponse)
def update_session(session_id: int, session_in: SessionUpdate, db: Session = Depends(get_db)):
    """更新训练会话属性"""
    db_session = SessionService.update_session(db, session_id, session_in)
    if not db_session:
        raise HTTPException(status_code=404, detail="会话未找到")
    return db_session


@router.post("/{session_id}/upload-video", response_model=MediaAssetResponse)
async def upload_video_file(session_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """上传本地训练视频，并启动后台异步动作/进球分析"""
    db_session = SessionService.get_session(db, session_id)
    if not db_session:
        raise HTTPException(status_code=404, detail="会话未找到")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    safe_name = Path(file.filename or "upload.mp4").name
    ext = Path(safe_name).suffix.lower()
    if ext not in {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}:
        raise HTTPException(status_code=400, detail="仅支持常见视频文件格式")

    file_path = os.path.join(UPLOAD_DIR, f"session_{session_id}_{safe_name}")
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 提取视频元数据
    cap = cv2.VideoCapture(file_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration = float(frame_count / fps) if fps > 0 else 0.0
    cap.release()

    media_asset = SessionService.save_media_asset(
        db,
        session_id=session_id,
        file_path=file_path,
        source_type="upload",
        fps=fps,
        res=f"{w}x{h}",
        duration=duration
    )

    SessionService.update_session(
        db,
        session_id,
        SessionUpdate(status="queued", notes=f"已上传本地视频: {safe_name}")
    )

    # 触发异步离线视觉分析任务
    analyze_video_offline_background(session_id, file_path)

    return media_asset


@router.get("/{session_id}/video/playback")
def play_session_video(session_id: int, db: Session = Depends(get_db)):
    """流式播放会话绑定的视频，供前端 UI 重放比对"""
    db_session = SessionService.get_session(db, session_id)
    if not db_session or not db_session.media_assets:
        raise HTTPException(status_code=404, detail="未找到对应的视频资源")

    # 默认播放第一个关联视频
    file_path = db_session.media_assets[0].file_path
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="视频文件在服务器上不存在")

    def video_streamer():
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(1024 * 1024)  # 1MB
                if not chunk:
                    break
                yield chunk

    return StreamingResponse(video_streamer(), media_type="video/mp4")


@router.websocket("/ws/{session_id}")
async def session_websocket_endpoint(
    websocket: WebSocket,
    session_id: int,
    compare_with_reference: bool = False,
    record: bool = False,
    use_server_camera: bool = False,
    camera_index: int = 0,
    db: Session = Depends(get_db)
):
    """
    WebSocket 实时推演双向通道
    - 支持客户端推帧 (client-driven)
    - 支持服务端调用本地 OpenCV 相机推流 (server-driven, 解决浏览器端相机权限问题)
    """
    db_session = SessionService.get_session(db, session_id)
    if not db_session:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    pose_proc = PoseProcessor()
    action_det = ActionDetector()
    ball_det = BallDetector()
    goal_det = GoalDetector()
    recorder = VideoRecorder(session_id) if record else None

    # 从会话中读取标定 H 矩阵
    H_matrix = None
    if db_session.calibration_data and "H" in db_session.calibration_data:
        H_matrix = db_session.calibration_data["H"]

    # 模式 A: 服务端直接读取本地 USB 相机并推流
    if use_server_camera:
        import asyncio
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            await websocket.send_json({"error": "无法打开服务端的 USB 相机"})
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
            return

        frame_idx = 0
        try:
            while True:
                ret, frame_bgr = cap.read()
                if not ret:
                    await asyncio.sleep(0.04)
                    continue

                ts_ms = frame_idx * 40.0 # 25 FPS

                # 1. 姿态解析
                pose_res = pose_proc.process_frame(frame_bgr, int(ts_ms))
                keypoints = pose_res["keypoints"]
                feet_pixel = pose_res["feet_pixel_midpoint"]

                # 2. 3D 投影
                feet_world = None
                skeleton_world_3d = None
                if feet_pixel and H_matrix:
                    try:
                        world_x, world_y = project_point_to_court(H_matrix, feet_pixel[0], feet_pixel[1])
                        feet_world = [world_x, world_y, 0.0]
                        
                        # 基于底面 3D 投影与 MediaPipe 相对世界地标，映射全关节到球场 3D 空间
                        if pose_res.get("world_keypoints"):
                            w_kps = pose_res["world_keypoints"]
                            lh_w = next((k for k in w_kps if k["name"] == "left_heel"), None)
                            rh_w = next((k for k in w_kps if k["name"] == "right_heel"), None)
                            if lh_w and rh_w:
                                anchor_x = (lh_w["x"] + rh_w["x"]) / 2.0
                                anchor_y = (lh_w["y"] + rh_w["y"]) / 2.0
                                anchor_z = (lh_w["z"] + rh_w["z"]) / 2.0
                                
                                skeleton_world_3d = {}
                                for kp in w_kps:
                                    x_c = feet_world[0] + (kp["x"] - anchor_x)
                                    y_c = feet_world[1] + (kp["z"] - anchor_z)
                                    z_c = max(0.0, anchor_y - kp["y"])
                                    skeleton_world_3d[kp["name"]] = [x_c, y_c, z_c]
                    except Exception:
                        pass

                # 3. 动作识别
                action_res = action_det.detect_action(keypoints)
                action_type = action_res["action_type"]
                metrics = action_res["metrics"]

                # 4. 比对
                comparisons = None
                if compare_with_reference and metrics:
                    comparisons = action_det.compare_metrics(metrics)

                # 5. 目标识别与进球判定
                ball_res = ball_det.detect_and_track(frame_bgr, frame_idx)
                ball_bbox = ball_res["ball_bbox"]
                hoop_bbox = ball_res["hoop_bbox"]
                ball_world = estimate_ball_world_from_bbox(ball_bbox, db_session.calibration_data)
                ball_depth_method = "pnp_ball_diameter"
                if ball_world is None:
                    ball_world = project_bbox_to_court(H_matrix, ball_bbox)
                    ball_depth_method = "homography_fallback"
                hoop_world = project_bbox_to_court(H_matrix, hoop_bbox, z=3.05)
                goal_event = goal_det.check_goal(ball_bbox, hoop_bbox, frame_idx)

                # 6. 服务端录制
                if recorder:
                    recorder.write_frame(frame_bgr)

                # 7. 将图像编码为 base64 回传，供网页渲染
                _, buffer = cv2.imencode('.jpg', frame_bgr)
                frame_b64 = base64.b64encode(buffer).decode('utf-8')
                frame_data_url = f"data:image/jpeg;base64,{frame_b64}"

                response_payload = WebSocketFrameOut(
                    frame_index=frame_idx,
                    timestamp_ms=ts_ms,
                    keypoints=keypoints,
                    feet_pixel=list(feet_pixel) if feet_pixel else None,
                    feet_world_3d=feet_world,
                    skeleton_world_3d=skeleton_world_3d,
                    action_type=action_type,
                    comparisons=comparisons,
                    goal_event=goal_event,
                    ball_bbox=ball_bbox,
                    hoop_bbox=hoop_bbox,
                    ball_world_3d=ball_world,
                    hoop_world_3d=hoop_world,
                    detector_meta={
                        "ball_detector": ball_res.get("detector"),
                        "confidence": ball_res.get("confidence", 0.0),
                        "model_path": ball_res.get("model_path"),
                        "model_error": ball_res.get("model_error"),
                        "depth_method": ball_depth_method,
                    },
                    frame=frame_data_url
                )
                await websocket.send_json(response_payload.model_dump())
                frame_idx += 1
                await asyncio.sleep(0.04)

        except WebSocketDisconnect:
            pass
        finally:
            cap.release()
            pose_proc.close()
            if recorder:
                recorder.stop_and_save(db)
                db.refresh(db_session)
        return

    # 模式 B: 客户端抓帧推送进行后台处理 (Client-driven)
    try:
        while True:
            data = await websocket.receive_json()
            
            frame_idx = data.get("frame_index", 0)
            ts_ms = data.get("timestamp_ms", 0.0)
            frame_b64 = data.get("frame", "")

            if "," in frame_b64:
                frame_b64 = frame_b64.split(",")[1]

            # 解密图像
            try:
                img_bytes = base64.b64decode(frame_b64)
                np_arr = np.frombuffer(img_bytes, dtype=np.uint8)
                frame_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            except Exception:
                continue

            if frame_bgr is None:
                continue

            # 1. 运行姿态解析
            pose_res = pose_proc.process_frame(frame_bgr, int(ts_ms))
            keypoints = pose_res["keypoints"]
            feet_pixel = pose_res["feet_pixel_midpoint"]

            # 2. 空间投影映射
            feet_world = None
            skeleton_world_3d = None
            if feet_pixel and H_matrix:
                try:
                    world_x, world_y = project_point_to_court(H_matrix, feet_pixel[0], feet_pixel[1])
                    feet_world = [world_x, world_y, 0.0]
                    
                    # 基于底面 3D 投影与 MediaPipe 相对世界地标，映射全关节到球场 3D 空间
                    if pose_res.get("world_keypoints"):
                        w_kps = pose_res["world_keypoints"]
                        lh_w = next((k for k in w_kps if k["name"] == "left_heel"), None)
                        rh_w = next((k for k in w_kps if k["name"] == "right_heel"), None)
                        if lh_w and rh_w:
                            anchor_x = (lh_w["x"] + rh_w["x"]) / 2.0
                            anchor_y = (lh_w["y"] + rh_w["y"]) / 2.0
                            anchor_z = (lh_w["z"] + rh_w["z"]) / 2.0
                            
                            skeleton_world_3d = {}
                            for kp in w_kps:
                                x_c = feet_world[0] + (kp["x"] - anchor_x)
                                y_c = feet_world[1] + (kp["z"] - anchor_z)
                                z_c = max(0.0, anchor_y - kp["y"])
                                skeleton_world_3d[kp["name"]] = [x_c, y_c, z_c]
                except Exception:
                    pass

            # 3. 运行动作分类
            action_res = action_det.detect_action(keypoints)
            action_type = action_res["action_type"]
            metrics = action_res["metrics"]

            # 4. 标准动作对比开关
            comparisons = None
            if compare_with_reference and metrics:
                comparisons = action_det.compare_metrics(metrics)

            # 5. 目标识别与进球判定
            ball_res = ball_det.detect_and_track(frame_bgr, frame_idx)
            ball_bbox = ball_res["ball_bbox"]
            hoop_bbox = ball_res["hoop_bbox"]
            ball_world = estimate_ball_world_from_bbox(ball_bbox, db_session.calibration_data)
            ball_depth_method = "pnp_ball_diameter"
            if ball_world is None:
                ball_world = project_bbox_to_court(H_matrix, ball_bbox)
                ball_depth_method = "homography_fallback"
            hoop_world = project_bbox_to_court(H_matrix, hoop_bbox, z=3.05)
            
            goal_event = goal_det.check_goal(ball_bbox, hoop_bbox, frame_idx)

            # 6. 服务端录制写入
            if recorder:
                recorder.write_frame(frame_bgr)

            # 7. 回传处理结果
            response_payload = WebSocketFrameOut(
                frame_index=frame_idx,
                timestamp_ms=ts_ms,
                keypoints=keypoints,
                feet_pixel=list(feet_pixel) if feet_pixel else None,
                feet_world_3d=feet_world,
                skeleton_world_3d=skeleton_world_3d,
                action_type=action_type,
                comparisons=comparisons,
                goal_event=goal_event,
                ball_bbox=ball_bbox,
                hoop_bbox=hoop_bbox,
                ball_world_3d=ball_world,
                hoop_world_3d=hoop_world,
                detector_meta={
                    "ball_detector": ball_res.get("detector"),
                    "confidence": ball_res.get("confidence", 0.0),
                    "model_path": ball_res.get("model_path"),
                    "model_error": ball_res.get("model_error"),
                    "depth_method": ball_depth_method,
                }
            )
            await websocket.send_json(response_payload.model_dump())

    except WebSocketDisconnect:
        pass
    finally:
        pose_proc.close()
        if recorder:
            recorder.stop_and_save(db)
            db.refresh(db_session)


@router.post("/{session_id}/calibrate", response_model=SessionResponse)
def calibrate_session_camera(
    session_id: int,
    payload: dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    接收前端 8 个像素点击点，计算单应性矩阵 H 与 PnP 位姿，并更新该训练会话的标定数据
    payload 格式: { "points": [[x1,y1], ..., [x8,y8]], "width": 640, "height": 480 }
    """
    db_session = SessionService.get_session(db, session_id)
    if not db_session:
        raise HTTPException(status_code=404, detail="会话未找到")
    
    points = payload.get("points", [])
    if len(points) != 8:
        raise HTTPException(status_code=400, detail="必须提供刚好 8 个标定点")
    
    width = payload.get("width", 640)
    height = payload.get("height", 480)
    
    from sport_vision.vision.calibration.calibration_tool import calibrate_from_points
    res = calibrate_from_points(points, (height, width))
    if not res:
        raise HTTPException(status_code=400, detail="标定解算失败")
    
    updated_data = db_session.calibration_data or {}
    updated_data["H"] = res["H"]
    updated_data["K"] = res["K"]
    updated_data["rvec"] = res["rvec"]
    updated_data["tvec"] = res["tvec"]
    updated_data["description"] = "通过 WebUI 标定向导重新计算得到的参数"
    
    from sport_vision.session.schemas import SessionUpdate
    SessionService.update_session(db, session_id, SessionUpdate(calibration_data=updated_data))
    
    return db_session
