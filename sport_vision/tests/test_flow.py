from __future__ import annotations

import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sport_vision.db.database import Base
# 导入所有领域模型注册到 metadata
from sport_vision.db import base
from sport_vision.athlete.services import AthleteService
from sport_vision.athlete.schemas import AthleteCreate, BodyHistoryCreate
from sport_vision.session.services import SessionService
from sport_vision.session.schemas import SessionCreate
from sport_vision.vision.calibration.calibration_tool import project_point_to_court

class TestSportVisionFlow(unittest.TestCase):
    def setUp(self):
        # 使用内存 SQLite 进行独立隔离的集成测试
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.close()

    def test_athlete_registration_and_trends(self):
        # 1. 注册运动员并登记初始身体指标
        athlete_in = AthleteCreate(
            name="张明",
            gender="male",
            age=17,
            position="guard",
            dominant_hand="right",
            initial_body=BodyHistoryCreate(
                height=188.5,
                weight=82.0,
                wingspan=196.0,
                body_fat=11.2
            )
        )
        athlete = AthleteService.create_athlete(self.db, athlete_in)
        self.assertIsNotNone(athlete.id)
        self.assertEqual(athlete.name, "张明")
        self.assertEqual(len(athlete.body_histories), 1)

        # 2. 追加身体历史变化记录
        AthleteService.add_body_history(
            self.db,
            athlete.id,
            BodyHistoryCreate(
                height=189.0,
                weight=83.5,
                wingspan=196.0,
                body_fat=10.8
            )
        )
        trends = AthleteService.get_body_history_trends(self.db, athlete.id)
        self.assertEqual(len(trends), 2)
        self.assertEqual(trends[1].weight, 83.5)

    def test_default_rules_initialization(self):
        # 验证默认规则在空库时自动生成
        rules = AthleteService.get_recommendation_rules(self.db, "youth", "guard")
        self.assertTrue(len(rules) > 0)
        
        # 校验手肘角度指标默认值
        elbow_rule = next(r for r in rules if r.metric_name == "elbow_angle_deg")
        self.assertEqual(elbow_rule.min_value, 75.0)
        self.assertEqual(elbow_rule.max_value, 155.0)

    def test_3d_homography_projection(self):
        # 预置单应性变换 H 矩阵，测试投影转换
        H = [
            [0.1, 0.0, 1.0],
            [0.0, 0.1, 2.0],
            [0.0, 0.0, 1.0]
        ]
        # x, y = (10, 20) -> (10*0.1 + 1.0)/1, (20*0.1 + 2.0)/1 = (2.0, 4.0)
        world_x, world_y = project_point_to_court(H, 10.0, 20.0)
        self.assertAlmostEqual(world_x, 2.0)
        self.assertAlmostEqual(world_y, 4.0)

    def test_ball_bbox_projection_helper(self):
        from sport_vision.vision.ball.ball_detector import project_bbox_to_court

        H = [
            [0.1, 0.0, 1.0],
            [0.0, 0.1, 2.0],
            [0.0, 0.0, 1.0]
        ]
        # bbox center = (20, 30), projected point = (3, 5)
        projected = project_bbox_to_court(H, [10, 20, 30, 40], z=0.25)
        self.assertEqual(projected, [3.0, 5.0, 0.25])

    def test_ball_world_estimation_from_pnp_bbox(self):
        from sport_vision.vision.ball.geometry_3d import estimate_ball_world_from_bbox

        calibration = {
            "K": [
                [1000.0, 0.0, 500.0],
                [0.0, 1000.0, 500.0],
                [0.0, 0.0, 1.0],
            ],
            "rvec": [[0.0], [0.0], [0.0]],
            "tvec": [[0.0], [0.0], [0.0]],
        }
        point = estimate_ball_world_from_bbox([450, 450, 550, 550], calibration, ball_diameter_m=0.24)
        self.assertIsNotNone(point)
        self.assertAlmostEqual(point[0], 0.0, places=5)
        self.assertAlmostEqual(point[1], 0.0, places=5)
        self.assertAlmostEqual(point[2], 2.4, places=5)

    def test_session_creation_and_metrics(self):
        # 1. 注册球员
        athlete = AthleteService.create_athlete(
            self.db,
            AthleteCreate(name="李华", gender="female", age=22, position="center", dominant_hand="left")
        )
        
        # 2. 创建训练会话
        session = SessionService.create_session(
            self.db,
            SessionCreate(
                athlete_id=athlete.id,
                source_type="camera",
                notes="测试会话",
                calibration_data={"H": [[1,0,0],[0,1,0],[0,0,1]]}
            )
        )
        self.assertIsNotNone(session.id)
        self.assertEqual(session.status, "created")

    def test_camera_intrinsics_and_pnp(self):
        from sport_vision.vision.camera.config import CAMERA_INTRINSICS
        from sport_vision.vision.calibration.calibration_tool import calibrate_from_points

        # 验证相机内参加载是否正确
        self.assertEqual(CAMERA_INTRINSICS["fx"], 1180.5)
        self.assertEqual(CAMERA_INTRINSICS["cx"], 960.0)

        # 模拟点击的 8 个像素坐标点
        dummy_clicks = [
            [200, 800], [1720, 800], [700, 700], [1220, 700],
            [900, 300], [1020, 300], [1020, 100], [900, 100]
        ]
        res = calibrate_from_points(dummy_clicks, (1080, 1920))
        self.assertIsNotNone(res)
        self.assertIn("H", res)
        self.assertIn("K", res)
        self.assertIn("rvec", res)
        self.assertIn("tvec", res)

    def test_3d_viz_class(self):
        from sport_vision.vision.calibration.viz_3d import Court3DVisualizer
        vis = Court3DVisualizer()
        self.assertEqual(vis.w, 15.24)
        self.assertEqual(vis.l, 28.65)
        self.assertEqual(vis.hoop_y, 1.60)

    def test_calibrate_endpoint_handler(self):
        athlete_in = AthleteCreate(
            name="李四",
            gender="male",
            age=22,
            position="center",
            dominant_hand="left",
            initial_body=BodyHistoryCreate(
                height=210.0, weight=110.0, wingspan=220.0, body_fat=13.5
            )
        )
        athlete = AthleteService.create_athlete(self.db, athlete_in)
        session_in = SessionCreate(
            athlete_id=athlete.id,
            session_type="shooting_drill",
            source_type="camera"
        )
        sess = SessionService.create_session(self.db, session_in)

        from sport_vision.session.endpoints import calibrate_session_camera
        dummy_clicks = [
            [200, 800], [1720, 800], [700, 700], [1220, 700],
            [900, 300], [1020, 300], [1020, 100], [900, 100]
        ]
        payload = {
            "points": dummy_clicks,
            "width": 1920,
            "height": 1080
        }
        res = calibrate_session_camera(sess.id, payload, self.db)
        self.assertIsNotNone(res)
        self.assertIsNotNone(res.calibration_data)
        self.assertIn("H", res.calibration_data)
        self.assertIn("rvec", res.calibration_data)


if __name__ == "__main__":
    unittest.main()
