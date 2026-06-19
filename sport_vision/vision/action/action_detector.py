from __future__ import annotations

import math
from typing import Dict, Any, List

from sport_vision.vision.action.config import STANDARD_SHOOTING_TEMPLATES

class ActionDetector:
    def __init__(self) -> None:
        self.frame_history: List[Dict[str, Any]] = []

    def detect_action(self, keypoints: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        基于当前帧的关键点估算技术指标，并进行简单的动作类型划分。
        """
        metrics = self._calculate_metrics(keypoints)
        action_type = "idle"

        # 基于姿态规则的简易动作状态判定
        if metrics:
            wrist_h = metrics.get("wrist_height_ratio") or 0.0
            elbow_a = metrics.get("elbow_angle_deg") or 180.0
            stance_w = metrics.get("stance_width_ratio") or 0.0

            if wrist_h > 0.45:
                action_type = "shooting"  # 手部抬高，判定为投篮出手动作
            elif wrist_h < 0.1 and stance_w > 0.45:
                action_type = "defense_stance"  # 低重心，宽站距，判定为防守姿势
            elif wrist_h < 0.2 and wrist_h > -0.2:
                action_type = "dribbling"  # 中等手部高度，运球
            else:
                action_type = "idle"

        return {
            "action_type": action_type,
            "metrics": metrics
        }

    def compare_metrics(self, metrics: Dict[str, float | None]) -> List[Dict[str, Any]]:
        """
        将实际测得的物理动作指标与标准模板进行比对，输出差异结果。
        """
        comparisons = []
        for name, reference in STANDARD_SHOOTING_TEMPLATES.items():
            val = metrics.get(name)
            status = "missing"
            
            if val is not None:
                if val < reference["min"]:
                    status = "low"
                elif val > reference["max"]:
                    status = "high"
                else:
                    status = "ok"

            comparisons.append({
                "name": name,
                "label": reference["label"],
                "value": val,
                "status": status,
                "min_value": reference["min"],
                "max_value": reference["max"]
            })
        return comparisons

    def _calculate_metrics(self, keypoints: List[Dict[str, Any]]) -> Dict[str, float | None]:
        """几何特征计算辅助函数"""
        kp_map = {kp["name"]: kp for kp in keypoints}

        def get_angle(p1_name, p2_name, p3_name):
            a, b, c = kp_map.get(p1_name), kp_map.get(p2_name), kp_map.get(p3_name)
            if not (a and b and c): return None
            ba = [a["x"] - b["x"], a["y"] - b["y"]]
            bc = [c["x"] - b["x"], c["y"] - b["y"]]
            norm_ba = math.sqrt(ba[0]**2 + ba[1]**2)
            norm_bc = math.sqrt(bc[0]**2 + bc[1]**2)
            if norm_ba == 0 or norm_bc == 0: return None
            cos_a = (ba[0]*bc[0] + ba[1]*bc[1]) / (norm_ba * norm_bc)
            cos_a = max(-1.0, min(1.0, cos_a))
            return math.degrees(math.acos(cos_a))

        def get_dist(p1_name, p2_name):
            a, b = kp_map.get(p1_name), kp_map.get(p2_name)
            if not (a and b): return 0.0
            return math.sqrt((a["x"]-b["x"])**2 + (a["y"]-b["y"])**2)

        left_elbow = get_angle("left_shoulder", "left_elbow", "left_wrist")
        right_elbow = get_angle("right_shoulder", "right_elbow", "right_wrist")
        elbow_angle = (left_elbow + right_elbow) / 2.0 if (left_elbow and right_elbow) else (left_elbow or right_elbow)

        left_knee = get_angle("left_hip", "left_knee", "left_ankle")
        right_knee = get_angle("right_hip", "right_knee", "right_ankle")
        knee_angle = (left_knee + right_knee) / 2.0 if (left_knee and right_knee) else (left_knee or right_knee)

        torso_lean = None
        shoulder_tilt = None
        wrist_height_ratio = None
        stance_width_ratio = None

        ls, rs = kp_map.get("left_shoulder"), kp_map.get("right_shoulder")
        lh, rh = kp_map.get("left_hip"), kp_map.get("right_hip")
        lw, rw = kp_map.get("left_wrist"), kp_map.get("right_wrist")
        la, ra = kp_map.get("left_ankle"), kp_map.get("right_ankle")

        if ls and rs and lh and rh:
            # 躯干倾角
            shoulder_mid = [(ls["x"] + rs["x"])/2, (ls["y"] + rs["y"])/2]
            hip_mid = [(lh["x"] + rh["x"])/2, (lh["y"] + rh["y"])/2]
            torso_vec = [shoulder_mid[0] - hip_mid[0], shoulder_mid[1] - hip_mid[1]]
            norm_torso = math.sqrt(torso_vec[0]**2 + torso_vec[1]**2)
            if norm_torso > 0:
                cos_lean = -torso_vec[1] / norm_torso  # 垂直夹角，Y 向上为负
                cos_lean = max(-1.0, min(1.0, cos_lean))
                torso_lean = math.degrees(math.acos(cos_lean))
            
            # 双肩倾角
            sh_vec = [rs["x"] - ls["x"], rs["y"] - ls["y"]]
            norm_sh = math.sqrt(sh_vec[0]**2 + sh_vec[1]**2)
            if norm_sh > 0:
                cos_tilt = sh_vec[0] / norm_sh
                cos_tilt = max(-1.0, min(1.0, cos_tilt))
                shoulder_tilt = math.degrees(math.acos(cos_tilt))

        if lh and rh and la and ra:
            # 比例指标
            hip_mid = [(lh["x"] + rh["x"])/2, (lh["y"] + rh["y"])/2]
            ankle_mid = [(la["x"] + ra["x"])/2, (la["y"] + ra["y"])/2]
            body_height = math.sqrt((hip_mid[0]-ankle_mid[0])**2 + (hip_mid[1]-ankle_mid[1])**2)
            
            if body_height > 0:
                wrist = lw if (lw and lw.get("visibility", 0) >= (rw.get("visibility", 0) if rw else 0)) else rw
                if wrist:
                    wrist_height_ratio = (hip_mid[1] - wrist["y"]) / body_height
                stance_width_ratio = get_dist("left_ankle", "right_ankle") / body_height

        return {
            "elbow_angle_deg": elbow_angle,
            "knee_angle_deg": knee_angle,
            "torso_lean_deg": torso_lean,
            "shoulder_tilt_deg": shoulder_tilt,
            "wrist_height_ratio": wrist_height_ratio,
            "stance_width_ratio": stance_width_ratio
        }
