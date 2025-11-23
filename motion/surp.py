# -*- coding: utf-8 -*-
import argparse, time, math
from sic_framework.core.sic_application import SICApplication
from sic_framework.core import sic_logging
from sic_framework.devices import Nao
from sic_framework.devices.common_naoqi.naoqi_motion import NaoPostureRequest, NaoqiMoveToRequest, NaoqiBreathingRequest
from sic_framework.devices.common_naoqi.naoqi_stiffness import Stiffness

# 可选功能：TTS / LED（若不可用会被忽略）
try:
    from sic_framework.devices.common_naoqi.naoqi_text_to_speech import NaoqiTextToSpeechRequest
    HAS_TTS = True
except Exception:
    HAS_TTS = False
try:
    from sic_framework.devices.common_naoqi.naoqi_leds import NaoLEDRequest
    HAS_LED = True
except Exception:
    HAS_LED = False

class Surprised(SICApplication):
    def __init__(self, ip):
        super(Surprised, self).__init__()
        self.set_log_level(sic_logging.INFO)
        self.ip = ip
        self.nao = None
        self.setup()

    def setup(self):
        self.nao = Nao(ip=self.ip)
        self.nao.stiffness.request(Stiffness(0.7, ["Body"]))
        try: self.nao.motion.request(NaoqiBreathingRequest(True))
        except Exception: pass
        try: self.nao.motion.request(NaoPostureRequest("StandInit", 0.6))
        except Exception: pass

    def flash_face(self, n=2, on_time=0.15, off_time=0.10):
        if not HAS_LED: return
        for _ in range(n):
            try:
                self.nao.leds.request(NaoLEDRequest("FaceLeds", True))
                time.sleep(on_time)
                self.nao.leds.request(NaoLEDRequest("FaceLeds", False))
                time.sleep(off_time)
            except Exception:
                break

    def run(self):
        try:
            # 1) “被吓到”向后小退一步 + 微抬身（Stand）
            try: self.nao.motion.request(NaoqiMoveToRequest(-0.10, 0.0, 0.0))
            except Exception: pass
            try: self.nao.motion.request(NaoPostureRequest("Stand", 0.5))
            except Exception: pass

            # 2) 快速环顾（用躯干左右小角度旋转替代“抬头左右看”）
            for theta in (math.radians(18), math.radians(-26), math.radians(12), 0.0):
                try: self.nao.motion.request(NaoqiMoveToRequest(0.0, 0.0, theta))
                except Exception: pass
                time.sleep(0.15)

            # 3) 面灯闪两次、说一句话
            self.flash_face()
            if HAS_TTS:
                self.nao.tts.request(NaoqiTextToSpeechRequest("哇！这是什么？太意外了！"))

        except Exception as e:
            self.logger.error("执行失败：%s", e)
        finally:
            try: self.nao.motion.request(NaoPostureRequest("Crouch", 0.5))
            except Exception: pass
            try: self.nao.stiffness.request(Stiffness(0.0, ["Body"]))
            except Exception: pass
            self.shutdown()

def main():
    ap = argparse.ArgumentParser(description="NAO 惊讶（无动画版）")
    ap.add_argument("--ip", required=True)
    args = ap.parse_args()
    app = Surprised(args.ip); app.run()

if __name__ == "__main__":
    main()
