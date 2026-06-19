from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

from sport_vision.vision.calibration.config import (
    COURT_LENGTH, COURT_WIDTH, HOOP_CENTER_Y, FT_LINE_Y, FT_LINE_HALF_WIDTH,
    THREE_PT_RADIUS, THREE_PT_CORNER_OFFSET
)

class Court3DVisualizer:
    """3D 篮球场简易模型交互可视化窗口"""
    def __init__(self, title: str = "3D Basketball Court Visualizer") -> None:
        self.title = title
        # 球场边界参数
        self.w = COURT_WIDTH
        self.l = COURT_LENGTH
        self.hoop_y = HOOP_CENTER_Y
        self.ft_y = FT_LINE_Y
        self.ft_w = FT_LINE_HALF_WIDTH
        self.r_3p = THREE_PT_RADIUS
        self.offset_3p = THREE_PT_CORNER_OFFSET

    def _draw_circle_3d(self, ax: Axes3D, center: tuple[float, float, float], radius: float, color: str = "white", alpha: float = 0.8) -> None:
        """在指定高度绘制 3D 圆弧"""
        theta = np.linspace(0, 2 * np.pi, 100)
        cx, cy, cz = center
        x = cx + radius * np.cos(theta)
        y = cy + radius * np.sin(theta)
        z = np.full_like(x, cz)
        ax.plot(x, y, z, color=color, alpha=alpha, linewidth=1.5)

    def _draw_arc_3d(self, ax: Axes3D, center: tuple[float, float, float], radius: float, theta_start: float, theta_end: float, color: str = "white") -> None:
        """绘制指定起始与截止角度的 3D 圆弧"""
        theta = np.linspace(theta_start, theta_end, 50)
        cx, cy, cz = center
        x = cx + radius * np.cos(theta)
        y = cy + radius * np.sin(theta)
        z = np.full_like(x, cz)
        ax.plot(x, y, z, color=color, alpha=0.8, linewidth=1.5)

    def draw_court(self, ax: Axes3D) -> None:
        """渲染简易 NBA 标准 3D 篮球场"""
        # 设置底色与风格
        ax.set_facecolor("#0F172A")
        ax.grid(False)
        
        # 1. 绘制球场边线及底线 (Z=0 地面)
        x_border = [-self.w / 2, self.w / 2, self.w / 2, -self.w / 2, -self.w / 2]
        y_border = [0, 0, self.l, self.l, 0]
        z_border = [0, 0, 0, 0, 0]
        ax.plot(x_border, y_border, z_border, color="white", linewidth=2.5, label="Boundary")

        # 中线
        ax.plot([-self.w/2, self.w/2], [self.l/2, self.l/2], [0, 0], color="white", linewidth=2.0)
        # 中圈 (半径 1.80m)
        self._draw_circle_3d(ax, (0.0, self.l / 2, 0.0), 1.80, color="white")

        # 2. 绘制双方罚球区与罚球线
        # 半场 A (Y = 0 侧)
        ax.plot([-self.ft_w, -self.ft_w, self.ft_w, self.ft_w], [0, self.ft_y, self.ft_y, 0], [0, 0, 0, 0], color="white", linewidth=1.5)
        self._draw_arc_3d(ax, (0, self.ft_y, 0), self.ft_w, 0, np.pi, color="white")
        # 半场 B (Y = L 侧)
        ax.plot([-self.ft_w, -self.ft_w, self.ft_w, self.ft_w], [self.l, self.l - self.ft_y, self.l - self.ft_y, self.l], [0, 0, 0, 0], color="white", linewidth=1.5)
        self._draw_arc_3d(ax, (0, self.l - self.ft_y, 0), self.ft_w, np.pi, 2 * np.pi, color="white")

        # 3. 绘制双方三分线
        # 半场 A
        corner_x = self.w / 2 - self.offset_3p
        # 直线部分
        ax.plot([-corner_x, -corner_x], [0, 4.26], [0, 0], color="white", linewidth=1.5)
        ax.plot([corner_x, corner_x], [0, 4.26], [0, 0], color="white", linewidth=1.5)
        # 弧线部分
        theta_start = np.arcsin((4.26 - self.hoop_y) / self.r_3p)
        self._draw_arc_3d(ax, (0, self.hoop_y, 0), self.r_3p, theta_start, np.pi - theta_start, color="white")

        # 半场 B
        ax.plot([-corner_x, -corner_x], [self.l, self.l - 4.26], [0, 0], color="white", linewidth=1.5)
        ax.plot([corner_x, corner_x], [self.l, self.l - 4.26], [0, 0], color="white", linewidth=1.5)
        self._draw_arc_3d(ax, (0, self.l - self.hoop_y, 0), self.r_3p, np.pi + theta_start, 2 * np.pi - theta_start, color="white")

        # 4. 绘制双方篮板与篮架结构
        # 半场 A 篮板 (宽度 1.83m，下沿高 2.90m，上沿高 3.95m，距底线 1.20m)
        bb_x = [-0.915, 0.915, 0.915, -0.915, -0.915]
        bb_y = [1.20, 1.20, 1.20, 1.20, 1.20]
        bb_z = [2.90, 2.90, 3.95, 3.95, 2.90]
        ax.plot(bb_x, bb_y, bb_z, color="#38BDF8", linewidth=2.0, label="Backboard")
        # 篮筐 (Y=1.60m, 高3.05m, 半径0.23m)
        self._draw_circle_3d(ax, (0.0, 1.60, 3.05), 0.23, color="#F97316")

        # 半场 B 篮板
        bb_y_b = [self.l - 1.20] * 5
        ax.plot(bb_x, bb_y_b, bb_z, color="#38BDF8", linewidth=2.0)
        # 篮筐 B
        self._draw_circle_3d(ax, (0.0, self.l - 1.60, 3.05), 0.23, color="#F97316")

    def draw_skeleton_3d(self, ax: Axes3D, joints: dict[str, tuple[float, float, float]] | None) -> None:
        """
        在 3D 空间中绘制人体骨架线条。
        joints 为字典，映射人体关键点名称到其在球场 3D 坐标系下的 [X, Y, Z] (单位：米)。
        """
        if not joints:
            return

        connections = [
            ("left_shoulder", "right_shoulder"),
            ("left_shoulder", "left_elbow"), ("left_elbow", "left_wrist"),
            ("right_shoulder", "right_elbow"), ("right_elbow", "right_wrist"),
            ("left_shoulder", "left_hip"), ("right_shoulder", "right_hip"),
            ("left_hip", "right_hip"),
            ("left_hip", "left_knee"), ("left_knee", "left_ankle"),
            ("right_hip", "right_knee"), ("right_knee", "right_ankle")
        ]

        # 绘制骨骼连线
        for p1, p2 in connections:
            if p1 in joints and p2 in joints:
                pt1 = joints[p1]
                pt2 = joints[p2]
                ax.plot(
                    [pt1[0], pt2[0]],
                    [pt1[1], pt2[1]],
                    [pt1[2], pt2[2]],
                    color="#00E5FF", linewidth=2.5, alpha=0.9
                )

        # 绘制关节散点
        for name, pt in joints.items():
            color = "#E040FB" if "wrist" in name or "ankle" in name else "#00E676"
            ax.scatter(pt[0], pt[1], pt[2], color=color, s=25, alpha=0.9)

    def show(self, 
             trajectory: list[list[float]] | None = None, 
             ball_arc: list[list[float]] | None = None,
             skeleton_joints: dict[str, tuple[float, float, float]] | None = None) -> None:
        """启动交互式可旋转与缩放的 3D 绘图窗口"""
        fig = plt.figure(figsize=(10, 7))
        # 显式使用 3d 投影
        ax = fig.add_subplot(111, projection='3d')
        fig.canvas.manager.set_window_title(self.title)

        self.draw_court(ax)

        # 绘制当前帧的 3D 人体骨架
        if skeleton_joints:
            self.draw_skeleton_3d(ax, skeleton_joints)

        # 绘制球员足底运动轨迹
        if trajectory and len(trajectory) > 0:
            traj_arr = np.array(trajectory)
            ax.plot(traj_arr[:, 0], traj_arr[:, 1], traj_arr[:, 2], 
                    color="#A855F7", linewidth=3, marker='o', markersize=4, label="Player Path")

        # 绘制篮球三维飞行抛物线
        if ball_arc and len(ball_arc) > 0:
            ball_arr = np.array(ball_arc)
            ax.plot(ball_arr[:, 0], ball_arr[:, 1], ball_arr[:, 2], 
                    color="#F97316", linewidth=2, linestyle='--', label="Ball Arc")

        # 设置坐标轴范围与比例
        ax.set_xlim(-self.w / 2 - 2, self.w / 2 + 2)
        ax.set_ylim(-2, self.l + 2)
        ax.set_zlim(0, 8)

        ax.set_xlabel("X (Width)")
        ax.set_ylabel("Y (Length)")
        ax.set_zlabel("Z (Height)")
        ax.legend()

        print("=== 3D 虚拟球场窗口已打开，您可以拖拽鼠标以旋转或平移视角 ===")
        plt.show()


# 命令行独立测试入口
if __name__ == "__main__":
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

    # 模拟球员从 Y=2 弧顶向 Y=6.5 移动的足底轨迹
    player_run = []
    for y in np.linspace(2, 6.5, 30):
        player_run.append([float(y * 0.2 - 0.5), float(y), 0.0])
    
    # 模拟篮球从手部 (X=1.1, Y=6.8, Z=1.7) 飞入篮筐 (X=0, Y=1.6, Z=3.05) 的抛物线
    t = np.linspace(0, 1, 20)
    ball_x = 1.1 * (1 - t) + 0.0 * t
    ball_y = 6.8 * (1 - t) + 1.6 * t
    ball_z = 1.7 * (1 - t) + 3.05 * t + 4.5 * (1 - t) * t  # 抛物线最高约 4 米

    ball_arc = list(zip(ball_x, ball_y, ball_z))
    
    vis.show(trajectory=player_run, ball_arc=ball_arc, skeleton_joints=dummy_skeleton)
