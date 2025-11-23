# -*- coding: utf-8 -*-
"""
NAO 情绪动作 Demo（关节级 + 动画兜底）

- 优先使用 SIC 的关节控制（SetAngles / AngleInterpolation）
- 如果当前 SIC 版本没有关节 Request，则退化为 NAO 自带情绪动画：
  - 生气：animations/Stand/Emotions/Negative/Angry_1
  - 开心：animations/Stand/Emotions/Positive/Happy_1
  - 难过：animations/Stand/Emotions/Negative/Sad_1

关节名参考 NAO 官方文档（HeadYaw, LShoulderPitch, LElbowYaw ... 等）。
"""

import argparse
import time
import importlib
from typing import Optional, List

from sic_framework.core.sic_application import SICApplication
from sic_framework.core import sic_logging
from sic_framework.devices import Nao
from sic_framework.devices.common_naoqi.naoqi_stiffness import Stiffness
from sic_framework.devices.common_naoqi.naoqi_motion import (
    NaoPostureRequest,
    NaoqiMoveToRequest,
    NaoqiAnimationRequest,
)

# --------- 动态发现 Request 类（兼容不同版本 SIC） ---------
MODULE_CANDIDATES = [
    "sic_framework.devices.common_naoqi.naoqi_motion",
    "sic_framework.devices.common_naoqi.naoqi_motion_messages",
    "sic_framework.devices.common_naoqi.naoqi_joint",
    "sic_framework.devices.common_naoqi.naoqi_joints",
]


def import_first(names: List[str]):
    for n in names:
        try:
            return importlib.import_module(n)
        except Exception:
            continue
    return None


def find_req(mod, must_all: List[str], any_of: List[str]):
    if not mod:
        return None
    # 先找“强匹配”，例如包含 set 和 angles 的类名
    for name in dir(mod):
        if not name.endswith("Request"):
            continue
        low = name.lower()
        if all(k in low for k in must_all):
            return getattr(mod, name)
    # 再找“弱匹配”，例如任意包含 angles 的
    for name in dir(mod):
        if not name.endswith("Request"):
            continue
        low = name.lower()
        if any(k in low for k in any_of):
            return getattr(mod, name)
    return None


# --------- 一些全局参数（幅度都在安全范围内） ---------
SPD_FAST = 0.35  # 关节角速度（0-1）
SPD_MED = 0.25

YAW_SWING = 0.35  # HeadYaw 左右摇头幅度（rad ≈ 20°）

STEP_BIG = 0.12   # 行走步长（m）
STEP_SMALL = 0.06


class EmotionJointsApp(SICApplication):
    def __init__(self, ip: str, mood: str = "angry"):
        super(EmotionJointsApp, self).__init__()
        self.set_log_level(sic_logging.INFO)

        self.ip = ip
        self.mood = mood
        self.nao = None

        # 尝试在本地 python 模块里找到各种 Request 类
        self.mod = import_first(MODULE_CANDIDATES)
        self.SetAnglesReq = find_req(self.mod, ["set", "angles"], ["angles"])
        self.AngleInterpReq = find_req(self.mod, ["angle", "interp"], ["interpolation", "interp"])
        self.GetAnglesReq = find_req(self.mod, ["get", "angles"], ["getangles", "anglesget"])

        self.has_joint_api = bool(self.SetAnglesReq or self.AngleInterpReq)

        self.setup()

    # ------------ 基础准备 ------------

    def setup(self):
        self.nao = Nao(ip=self.ip)

        self.logger.info(
            "Detected Requests: SetAngles=%s, AngleInterpolation=%s, GetAngles=%s",
            getattr(self.SetAnglesReq, "__name__", None),
            getattr(self.AngleInterpReq, "__name__", None),
            getattr(self.GetAnglesReq, "__name__", None),
        )

        if not self.has_joint_api:
            self.logger.warning(
                "未在当前 SIC 版本中发现关节角 Request（SetAngles/AngleInterpolation）。"
                "将使用 NAO 自带情绪动画作为兜底。"
            )

        # 上电 + 初始化站姿（能成就成，失败就算了）
        try:
            self.nao.stiffness.request(Stiffness(0.8, ["Body"]))
        except Exception:
            pass
        try:
            self.nao.motion.request(NaoPostureRequest("StandInit", 0.6))
        except Exception:
            pass

    # ------------ 通用小工具 ------------

    def set_angles(self, joints: List[str], targets: List[float], speed: float):
        """封装的关节角下发：优先 SetAngles，退化到 AngleInterpolation"""
        if not self.has_joint_api:
            # 没有关节 API 时，直接返回，不抛错
            self.logger.debug("set_angles 被调用，但当前没有关节 API，直接忽略。")
            return

        if self.SetAnglesReq:
            req = self.SetAnglesReq(joints, targets, speed)
            return self.nao.motion.request(req)

        if self.AngleInterpReq:
            # 用统一时长模拟一个“速度”的概念
            dur = max(0.25, 0.8 / max(1e-3, speed))
            req = self.AngleInterpReq(joints, [targets], [[dur] * len(joints)], True)
            return self.nao.motion.request(req)

        # 理论上走不到这里
        raise RuntimeError("无可用的关节设定请求")

    def get_angle(self, joint: str) -> Optional[float]:
        if not self.GetAnglesReq:
            return None
        req = self.GetAnglesReq([joint], True)
        vals = self.nao.motion.request(req)
        return float(vals[0])

    def play_animation(self, path: str):
        """播放 NAO 自带动画（作为关节控制的兜底）"""
        try:
            self.logger.info("Playing animation: %s", path)
            self.nao.motion.request(NaoqiAnimationRequest(path))
        except Exception as e:
            self.logger.error("播放动画 %s 失败：%s", path, e)

    # ------------ 生气：关节级 4 步动作（沿用你之前的设计） ------------

    def angry_phase1_knee_stomp(self, cycles=3):
        """原地抬腿并放下：右腿小幅快节奏弯伸 ×3"""
        RHipPitch0 = 0.0
        RKneePitch_up = 0.35   # 弯膝
        RHipPitch_up = -0.15   # 髋微屈配合
        RAnklePitch = -0.10    # 脚踝微调稳定

        for _ in range(cycles):
            # 弯曲
            self.set_angles(
                ["RHipPitch", "RKneePitch", "RAnklePitch"],
                [RHipPitch_up, RKneePitch_up, RAnklePitch],
                SPD_FAST,
            )
            time.sleep(0.20)
            # 回到大致直立
            self.set_angles(
                ["RHipPitch", "RKneePitch", "RAnklePitch"],
                [RHipPitch0, 0.0, 0.0],
                SPD_FAST,
            )
            time.sleep(0.12)

    def angry_phase2_point_forward(self):
        """右臂向前平举 + “伸指”（用略闭的手模拟）"""
        joints = [
            "RShoulderPitch",
            "RShoulderRoll",
            "RElbowYaw",
            "RElbowRoll",
            "RWristYaw",
            "RHand",
        ]
        targets = [
            0.25,   # 肩前抬
            -0.15,  # 肩轻外展
            1.20,   # 肘旋转
            0.10,   # 肘微伸
            0.00,   # 腕回正
            0.20,   # 手略闭，模拟只伸一指
        ]
        self.set_angles(joints, targets, SPD_MED)
        time.sleep(0.25)

    def angry_phase3_forward_and_shake(self):
        """向前两步 + 摇头"""
        for _ in range(2):
            try:
                self.nao.motion.request(NaoqiMoveToRequest(STEP_SMALL, 0.0, 0.0))
            except Exception:
                pass
            time.sleep(0.10)

        for _ in range(3):
            self.set_angles(["HeadYaw"], [YAW_SWING], SPD_FAST)
            time.sleep(0.18)
            self.set_angles(["HeadYaw"], [-YAW_SWING], SPD_FAST)
            time.sleep(0.18)

        self.set_angles(["HeadYaw"], [0.0], SPD_FAST)

    def angry_phase4_fight_stance(self):
        """右拳握紧，左腿略后撤，双手防守姿态"""
        # 右拳
        self.set_angles(
            ["RHand", "RShoulderPitch", "RShoulderRoll", "RElbowYaw", "RElbowRoll"],
            [0.0, 0.8, -0.10, 1.4, 0.8],
            SPD_MED,
        )
        # 左手收腰
        self.set_angles(
            ["LHand", "LShoulderPitch", "LShoulderRoll", "LElbowYaw", "LElbowRoll"],
            [0.0, 1.2, 0.15, -1.2, -0.6],
            SPD_MED,
        )
        # 左腿稍微后撤
        try:
            self.nao.motion.request(NaoqiMoveToRequest(-0.05, +0.03, 0.0))
        except Exception:
            pass

    def play_angry(self):
        if self.has_joint_api:
            self.logger.info("使用关节级『生气』动作")
            self.angry_phase1_knee_stomp()
            self.angry_phase2_point_forward()
            self.angry_phase3_forward_and_shake()
            self.angry_phase4_fight_stance()
        else:
            # 兜底：使用 NAO 自带“生气”动画（情绪包或手势包之一）
            self.logger.info("无关节 API，使用内置 Angry 动画")
            # 先试 Emotions/Negative/Angry_1，再失败就试 Gestures/Angry_1
            self.play_animation("animations/Stand/Emotions/Negative/Angry_1")
            # 额外再加一点“愤怒手势”
            self.play_animation("animations/Stand/Gestures/Angry_1")

    # ------------ 开心：双手挥舞 + 身体略前后晃 ------------

    def play_happy(self):
        if not self.has_joint_api:
            self.logger.info("无关节 API，使用内置 Happy 动画")
            self.play_animation("animations/Stand/Emotions/Positive/Happy_1")
            return

        self.logger.info("使用关节级『开心』动作")

        # Step 1：双臂举起，准备挥手
        joints = [
            "LShoulderPitch", "LShoulderRoll", "LElbowYaw", "LElbowRoll",
            "RShoulderPitch", "RShoulderRoll", "RElbowYaw", "RElbowRoll",
            "HeadPitch",
        ]
        targets = [
            1.0,  0.45, -1.0, -0.6,   # 左臂抬起略外展
            1.0, -0.45,  1.0,  0.6,   # 右臂抬起略外展
            -0.15,                     # 头微微上扬
        ]
        self.set_angles(joints, targets, SPD_MED)
        time.sleep(0.4)

        # Step 2：左右摆臂 3 次
        for _ in range(3):
            # 先向左“挥”
            self.set_angles(
                ["LElbowRoll", "RElbowRoll", "HeadYaw"],
                [-0.3, 0.9, 0.25],
                SPD_FAST,
            )
            time.sleep(0.25)
            # 再向右“挥”
            self.set_angles(
                ["LElbowRoll", "RElbowRoll", "HeadYaw"],
                [-0.9, 0.3, -0.25],
                SPD_FAST,
            )
            time.sleep(0.25)

        # Step 3：双臂略放松，但保持“开心”的张开姿态
        self.set_angles(
            [
                "LShoulderPitch", "LShoulderRoll", "LElbowYaw", "LElbowRoll",
                "RShoulderPitch", "RShoulderRoll", "RElbowYaw", "RElbowRoll",
                "HeadPitch", "HeadYaw",
            ],
            [
                1.2, 0.3, -1.2, -0.5,
                1.2, -0.3, 1.2, 0.5,
                -0.10, 0.0,
            ],
            SPD_MED,
        )
        time.sleep(0.4)

    # ------------ 难过：低头 + 双臂下垂抱在身前 ------------

    def play_sad(self):
        if not self.has_joint_api:
            self.logger.info("无关节 API，使用内置 Sad 动画")
            self.play_animation("animations/Stand/Emotions/Negative/Sad_1")
            return

        self.logger.info("使用关节级『难过』动作")

        # Step 1：低头 + 双肩内扣，手臂下垂到身前
        joints = [
            "HeadPitch", "HeadYaw",
            "LShoulderPitch", "LShoulderRoll", "LElbowYaw", "LElbowRoll", "LHand",
            "RShoulderPitch", "RShoulderRoll", "RElbowYaw", "RElbowRoll", "RHand",
        ]
        targets = [
            0.35, 0.0,       # 头向下
            1.5, 0.15, -1.0, -0.3, 0.3,  # 左臂前下垂，手半握
            1.5, -0.15, 1.0, 0.3, 0.3,   # 右臂前下垂，手半握
        ]
        self.set_angles(joints, targets, SPD_MED)
        time.sleep(0.6)

        # Step 2：身体略微前屈一点点，像是“叹气”
        self.set_angles(
            ["LHipPitch", "RHipPitch"],
            [0.15, 0.15],
            SPD_MED,
        )
        time.sleep(0.5)

        # Step 3：小幅度的左右轻晃，表现“失落”
        for _ in range(2):
            self.set_angles(["LShoulderRoll", "RShoulderRoll"], [0.25, -0.25], SPD_MED)
            time.sleep(0.3)
            self.set_angles(["LShoulderRoll", "RShoulderRoll"], [0.05, -0.05], SPD_MED)
            time.sleep(0.3)

    # ------------ 统一入口 ------------

    def run(self):
        try:
            # 确保大致站好
            try:
                self.nao.motion.request(NaoPostureRequest("Stand", 0.6))
                time.sleep(0.6)
            except Exception:
                pass

            if self.mood == "angry":
                self.play_angry()
            elif self.mood == "happy":
                self.play_happy()
            elif self.mood == "sad":
                self.play_sad()
            elif self.mood == "all":
                self.play_angry()
                time.sleep(1.0)
                self.play_happy()
                time.sleep(1.0)
                self.play_sad()
            else:
                self.logger.warning("未知 mood=%s，默认执行 angry", self.mood)
                self.play_angry()

        except Exception as e:
            self.logger.error("执行失败：%s", e)
        finally:
            # 安全收尾：回蹲姿 + 降刚度
            try:
                self.nao.motion.request(NaoPostureRequest("Crouch", 0.5))
            except Exception:
                pass
            try:
                self.nao.stiffness.request(Stiffness(0.0, ["Body"]))
            except Exception:
                pass
            self.shutdown()


def main():
    ap = argparse.ArgumentParser(description="NAO 情绪动作 Demo（关节级 + 动画兜底）")
    ap.add_argument("--ip", required=True, help="NAO 机器人 IP")
    ap.add_argument(
        "--mood",
        choices=["angry", "happy", "sad", "all"],
        default="angry",
        help="选择要执行的情绪动作",
    )
    args = ap.parse_args()

    app = EmotionJointsApp(args.ip, mood=args.mood)
    app.run()


if __name__ == "__main__":
    main()
