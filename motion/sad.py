# -*- coding: utf-8 -*-
import argparse, time, math
from sic_framework.core.sic_application import SICApplication
from sic_framework.core import sic_logging
from sic_framework.devices import Nao
from sic_framework.devices.common_naoqi.naoqi_motion import NaoPostureRequest, NaoqiMoveToRequest, NaoqiBreathingRequest
from sic_framework.devices.common_naoqi.naoqi_stiffness import Stiffness
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

class Sad(SICApplication):
    def __init__(self, ip):
        super(Sad, self).__init__()
        self.set_log_level(sic_logging.INFO)
        self.ip = ip
        self.nao = None
        self.setup()

    def setup(self):
        self.nao = Nao(ip=self.ip)
        self.nao.stiffness.request(Stiffness(0.6, ["Body"]))
        try: self.nao.motion.request(NaoqiBreathingRequest(True))
        except Exception: pass
        # 坐松/站稳
        try: self.nao.motion.request(NaoPostureRequest("SitRelax", 0.5))
        except Exception:
            try: self.nao.motion.request(NaoPostureRequest("StandInit", 0.5))
            except Exception: pass

    def soft_dim(self, cycles=3, on=0.25, off=0.25):
        if not HAS_LED: return
        for _ in range(cycles):
            try:
                self.nao.leds.request(NaoLEDRequest("FaceLeds", False))
                time.sleep(off)
                self.nao.leds.request(NaoLEDRequest("FaceLeds", True))
                time.sleep(on)
            except Exception:
                break

    def run(self):
        try:
            # 1) 微小摆身（左右极小旋转），营造“垂头丧气”
            for theta in (math.radians(6), math.radians(-8), math.radians(4), 0.0):
                try: self.nao.motion.request(NaoqiMoveToRequest(0.0, 0.0, theta))
                except Exception: pass
                time.sleep(0.4)

            # 2) 面灯缓慢明暗
            self.soft_dim(3, on=0.35, off=0.35)

            # 3) 轻叹气
            if HAS_TTS:
                self.nao.tts.request(NaoqiTextToSpeechRequest("唉……今天有点不开心。"))

            # 4) 慢慢站起再坐回（若可行）
            try:
                self.nao.motion.request(NaoPostureRequest("Stand", 0.4))
                time.sleep(0.4)
                self.nao.motion.request(NaoPostureRequest("SitRelax", 0.5))
            except Exception:
                pass

        except Exception as e:
            self.logger.error("执行失败：%s", e)
        finally:
            try: self.nao.motion.request(NaoPostureRequest("Crouch", 0.5))
            except Exception: pass
            try: self.nao.stiffness.request(Stiffness(0.0, ["Body"]))
            except Exception: pass
            self.shutdown()

def main():
    ap = argparse.ArgumentParser(description="NAO 悲伤（无动画版）")
    ap.add_argument("--ip", required=True)
    args = ap.parse_args()
    app = Sad(args.ip); app.run()

if __name__ == "__main__":
    main()
