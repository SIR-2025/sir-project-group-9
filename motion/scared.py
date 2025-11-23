# -*- coding: utf-8 -*-
import argparse, time, math
from sic_framework.core.sic_application import SICApplication
from sic_framework.core import sic_logging
from sic_framework.devices import Nao
from sic_framework.devices.common_naoqi.naoqi_motion import NaoPostureRequest, NaoqiMoveToRequest
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

class Afraid(SICApplication):
    def __init__(self, ip):
        super(Afraid, self).__init__()
        self.set_log_level(sic_logging.INFO)
        self.ip = ip
        self.nao = None
        self.setup()

    def setup(self):
        self.nao = Nao(ip=self.ip)
        self.nao.stiffness.request(Stiffness(0.7, ["Body"]))
        try: self.nao.motion.request(NaoPostureRequest("StandInit", 0.6))
        except Exception: pass

    def panic_scan(self):
        # 小幅左右转身两轮，模拟“慌张地张望”
        seq = [12, -16, 10, -12, 0]
        for deg in seq:
            try: self.nao.motion.request(NaoqiMoveToRequest(0.0, 0.0, math.radians(deg)))
            except Exception: pass
            time.sleep(0.14)

    def run(self):
        try:
            # 1) 连续小步后退（回避）
            for _ in range(3):
                try: self.nao.motion.request(NaoqiMoveToRequest(-0.06, 0.0, 0.0))
                except Exception: break
                time.sleep(0.12)

            # 2) 慌张环顾
            self.panic_scan()

            # 3) 斜退 + 再次环顾
            try: self.nao.motion.request(NaoqiMoveToRequest(-0.05, 0.03, math.radians(8)))
            except Exception: pass
            self.panic_scan()

            # 4) 面灯快速两闪 + 台词
            if HAS_LED:
                try:
                    self.nao.leds.request(NaoLEDRequest("FaceLeds", True));  time.sleep(0.12)
                    self.nao.leds.request(NaoLEDRequest("FaceLeds", False)); time.sleep(0.10)
                    self.nao.leds.request(NaoLEDRequest("FaceLeds", True));  time.sleep(0.12)
                    self.nao.leds.request(NaoLEDRequest("FaceLeds", False))
                except Exception: pass
            if HAS_TTS:
                self.nao.tts.request(NaoqiTextToSpeechRequest("有点害怕，我们离远一点吧。"))

        except Exception as e:
            self.logger.error("执行失败：%s", e)
        finally:
            try: self.nao.motion.request(NaoPostureRequest("Crouch", 0.5))
            except Exception: pass
            try: self.nao.stiffness.request(Stiffness(0.0, ["Body"]))
            except Exception: pass
            self.shutdown()

def main():
    ap = argparse.ArgumentParser(description="NAO 害怕（无动画版）")
    ap.add_argument("--ip", required=True)
    args = ap.parse_args()
    app = Afraid(args.ip); app.run()

if __name__ == "__main__":
    main()
