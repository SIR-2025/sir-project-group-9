# -*- coding: utf-8 -*-
"""
NAO motion replay demo application.

只负责：
- 连接 NAO
- 唤醒
- 上刚度
- 从当前文件夹加载已经录制好的动作文件 "motion_recorder_demo"
- 回放动作
- 最后让 NAO rest

录制部分已经在另一个脚本里完成。
"""

# Import basic preliminaries
from sic_framework.core.sic_application import SICApplication
from sic_framework.core import sic_logging

# Import the device(s) we will be using
from sic_framework.devices import Nao
from sic_framework.devices.common_naoqi.naoqi_autonomous import (
    NaoRestRequest,
    NaoWakeUpRequest,
)

# Import message types and requests
from sic_framework.devices.common_naoqi.naoqi_motion_recorder import (
    NaoqiMotionRecorderConf,
    NaoqiMotionRecording,
    PlayRecording,
)
from sic_framework.devices.common_naoqi.naoqi_stiffness import Stiffness


class NaoMotionReplayDemo(SICApplication):
    """
    NAO motion replay demo application.
    Replays an already recorded motion on a NAO robot.
    """

    def __init__(self):
        # Call parent constructor (handles singleton initialization)
        super(NaoMotionReplayDemo, self).__init__()

        # ---- 这里按需修改 ----
        self.nao_ip = "10.0.0.137"           # 你的 NAO IP
        self.motion_name = "motion_recorder_demo"  # 已录制动作文件名（无扩展名）
        self.chain = ["LArm", "RArm", "RLeg", "LLeg", "Head"]
        # ----------------------

        self.set_log_level(sic_logging.INFO)
        self.nao = None

        self.setup()

    def setup(self):
        """Initialize and configure the NAO robot for replay."""
        self.logger.info("Starting NAO Motion Replay Demo...")

        # 这里仍然给 Nao 传入 motion_record_conf，方便内部初始化 motion_record 连接器
        conf = NaoqiMotionRecorderConf(use_sensors=False)
        self.nao = Nao(self.nao_ip, motion_record_conf=conf)

    def run(self):
        """Main application logic: only replay an existing motion."""
        try:
            # 唤醒 NAO
            self.logger.info("Waking up NAO...")
            self.nao.autonomous.request(NaoWakeUpRequest())

            # 为回放动作开启刚度
            self.logger.info("Enabling stiffness for replay...")
            self.nao.stiffness.request(
                Stiffness(stiffness=0.7, joints=self.chain)
            )

            # 从当前文件夹加载之前保存的 motion
            self.logger.info(
                'Loading recorded motion from file: "%s"', self.motion_name
            )
            recording = NaoqiMotionRecording.load(self.motion_name)

            # 回放动作
            self.logger.info("Replaying recorded motion...")
            self.nao.motion_record.request(PlayRecording(recording))

            # 结束后进入 rest
            self.logger.info("Putting NAO to rest...")
            self.nao.autonomous.request(NaoRestRequest())

            self.logger.info("Motion replay demo completed successfully")

        except Exception as e:
            self.logger.error("Exception during replay: {}".format(e=e))
        finally:
            self.shutdown()


if __name__ == "__main__":
    demo = NaoMotionReplayDemo()
    demo.run()
