import random

import emoji

from astrobotany.items import Badge

taken = {badge.badge_symbol for badge in Badge.badges}

choices = []
for name, char in emoji.EMOJI_UNICODE["en"].items():

    # Stick to "simple" emojis
    if len(char) > 1:
        continue

    # No duplicates
    if char in taken:
        continue

    choices.append((name, char))


random.shuffle(choices)

# for name, char in choices:
#     print(char)

emojis = """
👙
⚡
🐶
🪁
🍦
😎
🥁
🎂
💽
🎻
🥗
🦘
🔮
🤺
📷
🥫
🦇
🦴
👄
🖖
🐓
🚛
🥖
💑
💄
💣
🥧
💸
🐦
💞
🕹
🧞
🥔
🦕
🐧
😘
💀
🏄
🤜
🧚
🏎
🤿
🎭
🥵
🐕
🪴
🏜
🍞
🐰
🍎
👯
🗿
🛼
🧙
🌯
🧉
👛
🧁
🤹
👀
🦟
🖕
🦩
⚽
🐙
🐤
🎃
🐞
😱
😜
🐝
💩
🐬
🍳
👒
🪅
🍀
🌅
🕊
🎱
💎
🌮
🎸
🔫
💃
🧬
🏝
🍷
🦦
🎣
🏵
🍔
👽
💾
🍍
🍙
🧋
🦢
🔊
🍭
"""

lines = emojis.strip().splitlines(keepends=False)
for i, char in enumerate(lines):
    name = emoji.demojize(char, delimiters=("", ""))
    name = name.replace("_", " ")
    print(f'badge_{i + 101} = Badge(name="{name}", series=2, number={i + 1}, symbol="{char}")')
