from __future__ import annotations

import argparse
import sys
import uvicorn
import cv2

from sport_vision.vision.calibration.calibration_tool import interactive_calibrate_from_frame

def run_server(host: str, port: int) -> None:
    """启动 FastAPI 服务"""
    print(f"=== 正在启动视觉篮球教练系统 Web 服务 ===")
    print(f"Host: {host}")
    print(f"Port: {port}")
    uvicorn.run("sport_vision.api.main:app", host=host, port=port, reload=False)


def calibrate(video_path: str) -> None:
    """运行三维空间平面标定测试"""
    cap = cv2.VideoCapture(video_path)
    ret, frame = cap.read()
    if not ret:
        print(f"错误: 无法读取视频文件 {video_path}")
        cap.release()
        return

    # 调用交互标定
    res = interactive_calibrate_from_frame(frame)
    cap.release()

    if res:
        print("\n标定计算成功！")
        print("解算出的单应性矩阵 H:")
        for row in res["H"]:
            print(f"  {row}")
        print("\n解算出的相机外参:")
        print(f"  rvec: {res['rvec']}")
        print(f"  tvec: {res['tvec']}")
        print("\n可以将此 H 矩阵作为会话的 calibration_data 传入，进行三维姿态投影推演。")
    else:
        print("标定已取消或求解失败。")


def run_3d_viz() -> None:
    """启动 3D 虚拟球场与模拟轨迹显示"""
    from sport_vision.vision.calibration.viz_3d import Court3DVisualizer
    import numpy as np

    vis = Court3DVisualizer()
    
    # 模拟一个站在三分线顶部的 3D 人体骨架线 (球员脚底在 X=0.8, Y=6.5, Z=0.0)
    dummy_skeleton = {
        "left_ankle": [0.6, 6.5, 0.0],
        "right_ankle": [1.0, 6.5, 0.0],
        "left_knee": [0.6, 6.5, 0.5],
        "right_knee": [1.0, 6.5, 0.5],
        "left_hip": [0.7, 6.5, 1.0],
        "right_hip": [0.9, 6.5, 1.0],
        "left_shoulder": [0.5, 6.5, 1.6],
        "right_shoulder": [1.1, 6.5, 1.6],
        "left_elbow": [0.4, 6.7, 1.3],
        "right_elbow": [1.2, 6.7, 1.3],
        "left_wrist": [0.5, 6.8, 1.7],
        "right_wrist": [1.1, 6.8, 1.7]
    }

    # 模拟球员折返跑与出手投篮轨迹
    player_run = []
    for y in np.linspace(2, 6.5, 30):
        player_run.append([float(y * 0.2 - 0.5), float(y), 0.0])
    
    # 模拟篮球抛物线 (出手点 -> 篮筐)
    t = np.linspace(0, 1, 20)
    ball_x = 0.8 * (1 - t) + 0.0 * t
    ball_y = 6.5 * (1 - t) + 1.6 * t
    ball_z = 2.2 * (1 - t) + 3.05 * t + 4 * (1 - t) * t

    ball_arc = list(zip(ball_x, ball_y, ball_z))
    vis.show(trajectory=player_run, ball_arc=ball_arc, skeleton_joints=dummy_skeleton)


def main() -> None:
    parser = argparse.ArgumentParser(description="视觉篮球教练智能分析系统命令行入口")
    subparsers = parser.add_subparsers(dest="command", help="子命令类型")

    # 1. 运行服务器命令
    server_parser = subparsers.add_parser("run-server", help="启动 FastAPI 后端 Web 服务和 Web UI")
    server_parser.add_argument("--host", type=str, default="127.0.0.1", help="绑定 IP")
    server_parser.add_argument("--port", type=int, default=8000, help="绑定端口")

    # 2. 本地标定测试命令
    calibrate_parser = subparsers.add_parser("calibrate", help="运行本地视频帧 3D 标定交互解算")
    calibrate_parser.add_argument("--video", type=str, required=True, help="视频路径")

    # 3. 3D 可视化测试命令
    subparsers.add_parser("run-3d-viz", help="启动可旋转及缩放的 3D 虚拟球场三维窗口")

    args = parser.parse_args()

    if args.command == "run-server":
        run_server(args.host, args.port)
    elif args.command == "calibrate":
        calibrate(args.video)
    elif args.command == "run-3d-viz":
        run_3d_viz()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
