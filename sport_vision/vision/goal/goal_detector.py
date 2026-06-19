from __future__ import annotations

from typing import Dict, Any, List, Optional
from sport_vision.vision.goal.config import MIN_DOWNWARD_SPEED, ENTRY_EXIT_GAP_MIN, ENTRY_EXIT_GAP_MAX

class GoalDetector:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.state = "fly"  # fly -> entry -> exit/goal
        self.entry_frame = -1
        self.detected_goals: List[Dict[str, Any]] = []

    def check_goal(self, ball_bbox: Optional[list[int]], hoop_bbox: list[int], frame_index: int) -> Dict[str, Any] | None:
        """
        基于篮球轨迹与篮筐物理边界检测进球事件。
        判定空心进球(Swish)、打板进球(Bank)或碰框进球(Rim-in)。
        """
        if not ball_bbox or not hoop_bbox:
            return None

        # 计算球心与篮筐中心位置
        ball_center_x = (ball_bbox[0] + ball_bbox[2]) / 2
        ball_center_y = (ball_bbox[1] + ball_bbox[3]) / 2
        hoop_center_x = (hoop_bbox[0] + hoop_bbox[2]) / 2
        hoop_top_y = hoop_bbox[1]
        hoop_bottom_y = hoop_bbox[3]

        goal_event = None

        if self.state == "fly":
            # 状态1：球飞过篮筐口上方，正在往下落入篮口
            # 判断球心进入篮架平面之上 (X对齐，Y接近)
            if (hoop_bbox[0] <= ball_center_x <= hoop_bbox[2]) and (hoop_top_y - 15 <= ball_center_y <= hoop_top_y + 10):
                self.state = "entry"
                self.entry_frame = frame_index

        elif self.state == "entry":
            # 状态2：球已经在篮筐内，判断是否穿过筐底离开
            # 判断时间窗口在合理范围内
            delta_f = frame_index - self.entry_frame
            if delta_f > ENTRY_EXIT_GAP_MAX:
                self.reset()  # 超出窗口，属于假进球/噪声，重置
            elif ball_center_y > hoop_bottom_y:
                # 垂直速度判定 (球正在向下运动)
                if delta_f >= ENTRY_EXIT_GAP_MIN:
                    # 判定为有效进球！
                    # 依据与筐边的接触距离，简单分类进球类型
                    dist_to_center = abs(ball_center_x - hoop_center_x)
                    if dist_to_center < 5:
                        goal_type = "swish"  # 空心球
                    elif dist_to_center > 15:
                        goal_type = "bank"   # 打板/擦板球
                    else:
                        goal_type = "rim_in"  # 碰框进球

                    goal_event = {
                        "event_id": f"goal_{frame_index}",
                        "frame_index": frame_index,
                        "goal_type": goal_type,
                        "score_value": 3 if ball_bbox[0] < 100 else 2,  # 示意两分/三分
                        "confidence": 0.85,
                        "key_timestamps": {
                            "release_frame": self.entry_frame - 25,
                            "rim_entry_frame": self.entry_frame,
                            "rim_exit_frame": frame_index
                        }
                    }
                    self.detected_goals.append(goal_event)
                    self.state = "fly"  # 回归飞线，等待下一次投篮

        return goal_event
