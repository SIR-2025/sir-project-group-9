# -*- coding: utf-8 -*-
"""
SIC 动画版示例：举左手 -> 举右手 -> 摇头
- 仅使用 NaoqiAnimationRequest / NaoPostureRequest
- 为不同固件准备多个候选动画名，逐一尝试直到成功
"""
import argparse, time
from sic_framework.core.sic_application import SICApplication
from sic_framework.core import sic_logging
from sic_framework.devices import Nao
from sic_framework.devices.common_naoqi.naoqi_motion import (
    NaoPostureRequest,
    NaoqiAnimationRequest,
)
from sic_framework.devices.common_naoqi.naoqi_stiffness import Stiffness

# 常见可用的手臂/头部动画候选（按优先级排列；不同镜像可能只有其中一部分存在）
CANDIDATES = {
    "left_raise": [
        # 左手举起/挥手类
        "animations/Stand/Gestures/Hey_3",           # 常见左手版本
        "animations/Stand/Gestures/YouKnowWhat_1",
        "animations/Stand/Gestures/Enthusiastic_4",
        "animations/Stand/Gestures/You_3",
        # 退而求其次：双手/含左手参与
        "animations/Stand/Emotions/Positive_3",
        "animations/Stand/Emotions/Excited_1",
    ],
    "right_raise": [
        "animations/Stand/Gestures/Hey_1",           # 经典右手挥手
        "animations/Stand/Gestures/YouKnowWhat_3",
        "animations/Stand/Gestures/You_1",
        "animations/Stand/Gestures/Enthusiastic_1",
        "animations/Stand/Gestures/Hey_5",
    ],
    "shake_head": [
        # 摇头（否定）类
        "animations/Stand/Emotions/Negative_1",
        "animations/Stand/Emotions/Negative_2",
        "animations/Stand/Gestures/No_1",
        "animations/Stand/Gestures/No_2",
        "animations/Stand/Gestures/No_3",
    ],
}

class Demo(SICApplication):
    def __init__(self, ip: str):
        super(Demo, self).__init__()
        self.set_log_level(sic_logging.INFO)
        self.nao_ip = ip
        self.nao = None
        self.setup()

    def setup(self):
        self.nao = Nao(ip=self.nao_ip)
        # 上刚度 & 站稳
        try:
            self.nao.stiffness.request(Stiffness(0.7, ["Body"]))
        except Exception as e:
            self.logger.warning(f"设置刚度失败：{e}")
        try:
            self.nao.motion.request(NaoPostureRequest("StandInit", 0.5))
        except Exception as e:
            self.logger.warning(f"初始姿态失败（可忽略）：{e}")

    def play_first_available(self, keys, label):
        """依次尝试一组动画名，成功即返回 True；全部失败则抛出最后一个异常。"""
        last_err = None
        for k in keys:
            try:
                self.logger.info(f"尝试动画：{k}")
                self.nao.motion.request(NaoqiAnimationRequest(k))
                self.logger.info(f"{label} OK：{k}")
                return True
            except Exception as e:
                last_err = e
                self.logger.debug(f"动画不可用：{k} -> {e}")
                continue
        raise RuntimeError(f"{label} 动作在此镜像未找到可用动画。最后错误：{last_err}")

    def run(self):
        try:
            # 举左手
            self.play_first_available(CANDIDATES["left_raise"], "举左手")
            time.sleep(0.5)

            # 举右手
            self.play_first_available(CANDIDATES["right_raise"], "举右手")
            time.sleep(0.5)

            # 摇头
            self.play_first_available(CANDIDATES["shake_head"], "摇头")

        except Exception as e:
            self.logger.error(f"执行失败：{e}")
        finally:
            # 安全收尾
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
    ap = argparse.ArgumentParser(description="SIC 动画版：举左手/举右手/摇头")
    ap.add_argument("--ip", default = "10.0.0.137", help="NAO 机器人 IP")
    args = ap.parse_args()
    app = Demo(args.ip)
    try:
        app.run()
    finally:
        pass

if __name__ == "__main__":
    main()
