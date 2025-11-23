# -*- coding: utf-8 -*-
"""
motion_animations_demo.py

使用 Social Interaction Cloud (SIC) 通过 NAO 自带的动画接口：
- 列出并打印以下两个路径下的所有预定义动画：
    * animations/Stand/Emotions/Negative
    * animations/Stand/Gestures
- 选择并表演其中任意一个动画

注意：
- 这里只使用 sic_framework，不直接使用 naoqi / qi SDK。
- 动画列表来自 NAO 官方文档与示例输出，如果你的机器人上安装了自定义行为，
  它们不会自动出现在本列表中，需要你自己手动添加。
"""

from __future__ import print_function

import argparse
import sys

from sic_framework.devices import Nao
from sic_framework.devices.common_naoqi.naoqi_motion import (
    NaoPostureRequest,
    NaoqiAnimationRequest,
)

# ---------------------------------------------------------------------------
# 1. 预定义动画列表
# ---------------------------------------------------------------------------

NEGATIVE_EMOTION_ANIMATIONS = [
    "animations/Stand/Emotions/Negative/Angry_1",
    "animations/Stand/Emotions/Negative/Angry_2",
    "animations/Stand/Emotions/Negative/Angry_3",
    "animations/Stand/Emotions/Negative/Angry_4",
    "animations/Stand/Emotions/Negative/Anxious_1",
    "animations/Stand/Emotions/Negative/Bored_1",
    "animations/Stand/Emotions/Negative/Bored_2",
    "animations/Stand/Emotions/Negative/Disappointed_1",
    "animations/Stand/Emotions/Negative/Exhausted_1",
    "animations/Stand/Emotions/Negative/Exhausted_2",
    "animations/Stand/Emotions/Negative/Fear_1",
    "animations/Stand/Emotions/Negative/Fear_2",
    "animations/Stand/Emotions/Negative/Fearful_1",
    "animations/Stand/Emotions/Negative/Frustrated_1",
    "animations/Stand/Emotions/Negative/Humiliated_1",
    "animations/Stand/Emotions/Negative/Hurt_1",
    "animations/Stand/Emotions/Negative/Hurt_2",
    "animations/Stand/Emotions/Negative/Late_1",
    "animations/Stand/Emotions/Negative/Sad_1",
    "animations/Stand/Emotions/Negative/Sad_2",
    "animations/Stand/Emotions/Negative/Shocked_1",
    "animations/Stand/Emotions/Negative/Sorry_1",
    "animations/Stand/Emotions/Negative/Surprise_1",
    "animations/Stand/Emotions/Negative/Surprise_2",
    "animations/Stand/Emotions/Negative/Surprise_3",
]

GESTURE_ANIMATIONS = [
    # 来自示例输出
    "animations/Stand/Gestures/Angry_1",
    "animations/Stand/Gestures/Angry_2",
    "animations/Stand/Gestures/Angry_3",
    "animations/Stand/Gestures/BowShort_1",
    "animations/Stand/Gestures/BowShort_2",
    "animations/Stand/Gestures/BowShort_3",
    "animations/Stand/Gestures/But_1",
    "animations/Stand/Gestures/CalmDown_1",
    "animations/Stand/Gestures/CalmDown_2",
    "animations/Stand/Gestures/CalmDown_3",
    "animations/Stand/Gestures/CalmDown_4",
    "animations/Stand/Gestures/CalmDown_5",
    "animations/Stand/Gestures/CalmDown_6",
    "animations/Stand/Gestures/Choice_1",
    "animations/Stand/Gestures/ComeOn_1",
    "animations/Stand/Gestures/Confused_1",
    "animations/Stand/Gestures/Confused_2",
    "animations/Stand/Gestures/CountFive_1",
    "animations/Stand/Gestures/CountFour_1",
    "animations/Stand/Gestures/CountMore_1",
    "animations/Stand/Gestures/CountOne_1",
    "animations/Stand/Gestures/CountThree_1",
    "animations/Stand/Gestures/CountTwo_1",
    "animations/Stand/Gestures/Desperate_1",
    "animations/Stand/Gestures/Desperate_2",
    "animations/Stand/Gestures/Desperate_3",
    "animations/Stand/Gestures/Desperate_4",
    "animations/Stand/Gestures/Desperate_5",
    "animations/Stand/Gestures/DontUnderstand_1",
    "animations/Stand/Gestures/Enthusiastic_3",
    "animations/Stand/Gestures/Enthusiastic_4",
    "animations/Stand/Gestures/Enthusiastic_5",
    "animations/Stand/Gestures/Everything_1",
    "animations/Stand/Gestures/Everything_2",
    "animations/Stand/Gestures/Everything_3",
    "animations/Stand/Gestures/Everything_4",
    "animations/Stand/Gestures/Everything_6",
    "animations/Stand/Gestures/Excited_1",
    "animations/Stand/Gestures/Explain_1",
    "animations/Stand/Gestures/Explain_2",
    "animations/Stand/Gestures/Explain_3",
    "animations/Stand/Gestures/Explain_4",
    "animations/Stand/Gestures/Explain_5",
    "animations/Stand/Gestures/Explain_6",
    "animations/Stand/Gestures/Explain_7",
    "animations/Stand/Gestures/Explain_8",
    "animations/Stand/Gestures/Explain_10",
    "animations/Stand/Gestures/Explain_11",
    "animations/Stand/Gestures/Far_1",
    "animations/Stand/Gestures/Far_2",
    "animations/Stand/Gestures/Far_3",
    "animations/Stand/Gestures/Follow_1",
    "animations/Stand/Gestures/Give_1",
    "animations/Stand/Gestures/Give_2",
    "animations/Stand/Gestures/Give_3",
    "animations/Stand/Gestures/Give_4",
    "animations/Stand/Gestures/Give_5",
    "animations/Stand/Gestures/Give_6",
    "animations/Stand/Gestures/Great_1",
    "animations/Stand/Gestures/HeSays_1",
    "animations/Stand/Gestures/HeSays_2",
    "animations/Stand/Gestures/HeSays_3",
    # 来自 Aldebaran 官方 NAO 动画表（补充缺失的几个）
    "animations/Stand/Gestures/Hey_1",
    "animations/Stand/Gestures/Hey_6",
    "animations/Stand/Gestures/IDontKnow_1",
    "animations/Stand/Gestures/IDontKnow_2",
    "animations/Stand/Gestures/Me_1",
    "animations/Stand/Gestures/Me_2",
    "animations/Stand/Gestures/No_3",
    "animations/Stand/Gestures/No_8",
    "animations/Stand/Gestures/No_9",
    "animations/Stand/Gestures/Please_1",
    "animations/Stand/Gestures/Yes_1",
    "animations/Stand/Gestures/Yes_2",
    "animations/Stand/Gestures/Yes_3",
    "animations/Stand/Gestures/YouKnowWhat_1",
    "animations/Stand/Gestures/YouKnowWhat_5",
    "animations/Stand/Gestures/You_1",
    "animations/Stand/Gestures/You_4",
]

ALL_ANIMATIONS = NEGATIVE_EMOTION_ANIMATIONS + GESTURE_ANIMATIONS


# ---------------------------------------------------------------------------
# 2. 打印文件名工具函数
# ---------------------------------------------------------------------------

def print_animation_lists():
    """打印两个路径下所有预定义动画名称。"""
    print("=" * 60)
    print("animations/Stand/Emotions/Negative  下的预定义动画:")
    for idx, name in enumerate(NEGATIVE_EMOTION_ANIMATIONS):
        print("[{:02d}] {}".format(idx, name))

    print("\n" + "=" * 60)
    print("animations/Stand/Gestures           下的预定义动画:")
    offset = len(NEGATIVE_EMOTION_ANIMATIONS)
    for i, name in enumerate(GESTURE_ANIMATIONS):
        print("[{:02d}] {}".format(i + offset, name))

    print("=" * 60)
    print("总计 {} 个动画.".format(len(ALL_ANIMATIONS)))


# ---------------------------------------------------------------------------
# 3. 应用主类：连接 NAO 并表演动画
# ---------------------------------------------------------------------------

class MotionAnimationsApp(object):
    def __init__(self, nao_ip, auto_stand=True):
        """
        :param nao_ip: 机器人 IP 地址
        :param auto_stand: 在播放动画前是否自动切到 Stand 姿势
        """
        self.nao_ip = nao_ip
        self.auto_stand = auto_stand
        self.nao = None

    # ------ 初始化 & 姿势控制 ------
    def setup(self):
        """初始化 NAO 设备对象。"""
        print("[INFO] Connecting to Nao at {} via SIC...".format(self.nao_ip))
        # 这里不会直接使用 naoqi，仅通过 SIC 的 Nao 封装
        self.nao = Nao(ip=self.nao_ip)
        print("[INFO] Nao device created.")

    def go_to_stand(self):
        """让 NAO 切到 Stand 姿势（如果需要）。"""
        if not self.auto_stand:
            return

        print("[INFO] Going to Stand posture...")
        try:
            self.nao.motion.request(NaoPostureRequest("Stand", 0.5))
        except Exception as exc:  # pylint: disable=broad-except
            print("[WARN] Failed to change posture to Stand: {}".format(exc))

    # ------ 动画播放 ------
    def play_animation(self, animation_name):
        """播放指定名称的动画。"""
        print("[INFO] Playing animation: {}".format(animation_name))
        try:
            self.nao.motion.request(NaoqiAnimationRequest(animation_name))
        except Exception as exc:  # pylint: disable=broad-except
            print("[ERROR] Failed to play animation {}: {}".format(animation_name, exc))

    # ------ 交互式命令行 ------
    def interactive_loop(self):
        """简单的命令行交互，可以通过索引或名称选择动画播放。"""
        if self.nao is None:
            self.setup()

        self.go_to_stand()
        print_animation_lists()

        print("\n输入动画的 索引 或 全路径 / 结尾名称 进行播放，例如：")
        print("  - 0            # 播放列表中第 0 个动画")
        print("  - Angry_1      # 根据结尾匹配")
        print("  - animations/Stand/Gestures/Hey_1")
        print("输入 'list' 重新打印列表，输入 'q' / 'quit' 退出。\n")

        if sys.version_info[0] < 3:
            input_func = raw_input  # type: ignore[name-defined]
        else:
            input_func = input

        while True:
            try:
                user_input = input_func("选择动画> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n[INFO] Bye.")
                break

            if not user_input:
                continue

            if user_input.lower() in ("q", "quit", "exit"):
                print("[INFO] Quit.")
                break

            if user_input.lower() in ("l", "list"):
                print_animation_lists()
                continue

            # 尝试把输入当作索引
            if user_input.isdigit():
                idx = int(user_input)
                if 0 <= idx < len(ALL_ANIMATIONS):
                    self.play_animation(ALL_ANIMATIONS[idx])
                else:
                    print("[WARN] 索引超出范围 0-{}.".format(len(ALL_ANIMATIONS) - 1))
                continue

            # 若不是纯数字，则尝试匹配路径或结尾名称
            # 完整路径（以 animations/ 开头）
            anim_name = None
            if user_input.startswith("animations/"):
                if user_input in ALL_ANIMATIONS:
                    anim_name = user_input
                else:
                    print("[WARN] 在预定义列表中找不到该动画：{}".format(user_input))
                    continue
            else:
                # 根据结尾名称匹配，比如 "Angry_1"
                matches = [
                    name for name in ALL_ANIMATIONS
                    if name.endswith("/" + user_input)
                ]
                if len(matches) == 1:
                    anim_name = matches[0]
                elif len(matches) > 1:
                    print("[WARN] 名称不唯一，匹配到多个动画：")
                    for m in matches:
                        print("  -", m)
                    continue
                else:
                    print("[WARN] 找不到名称包含 '{}' 的动画。".format(user_input))
                    continue

            if anim_name:
                self.play_animation(anim_name)


# ---------------------------------------------------------------------------
# 4. 命令行入口
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="列出并播放 NAO 预定义情绪/手势动画 (SIC, 无 naoqi 直接调用)"
    )
    parser.add_argument(
        "--ip",
        "-i",
        required=True,
        help="NAO 机器人的 IP 地址",
    )
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="仅输出动画列表，不连接机器人、不播放动作",
    )
    parser.add_argument(
        "--no-stand",
        action="store_true",
        help="不要在播放前自动切换到 Stand 姿势",
    )
    parser.add_argument(
        "--play",
        help=(
            "直接播放指定动画，而不是进入交互模式；"
            "可以是索引 (整数) 或 动画结尾名称 / 全路径"
        ),
    )

    args = parser.parse_args()

    # 1) 仅打印列表的模式
    if args.list_only:
        print_animation_lists()
        return

    # 2) 需要实际连接 NAO 的模式
    app = MotionAnimationsApp(nao_ip=args.ip, auto_stand=not args.no_stand)

    app.setup()
    app.go_to_stand()

    if args.play:
        # 直接播放一次（复用和交互模式一样的解析逻辑）
        user_input = args.play.strip()
        if user_input.isdigit():
            idx = int(user_input)
            if 0 <= idx < len(ALL_ANIMATIONS):
                app.play_animation(ALL_ANIMATIONS[idx])
            else:
                print("[WARN] 索引超出范围 0-{}.".format(len(ALL_ANIMATIONS) - 1))
        elif user_input.startswith("animations/"):
            if user_input in ALL_ANIMATIONS:
                app.play_animation(user_input)
            else:
                print("[WARN] 在预定义列表中找不到该动画：{}".format(user_input))
        else:
            matches = [
                name for name in ALL_ANIMATIONS
                if name.endswith("/" + user_input)
            ]
            if len(matches) == 1:
                app.play_animation(matches[0])
            elif len(matches) > 1:
                print("[WARN] 名称不唯一，匹配到多个动画：")
                for m in matches:
                    print("  -", m)
            else:
                print("[WARN] 找不到名称包含 '{}' 的动画。".format(user_input))
    else:
        # 进入交互式循环
        app.interactive_loop()


if __name__ == "__main__":
    main()
