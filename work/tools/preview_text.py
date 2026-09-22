# -*- coding: utf-8 -*-
"""빌드된 M_MSG.S8 의 항목을 패치된 게임 글꼴로 그려 본다 (화면 확인용).

사용: python work/tools/preview_text.py <출력.png> [group:entry ...]
"""
import os
import struct
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import font8
import s8text
import units

ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
MSG = os.path.join(ROOT, "work", "patched", "M_MSG.S8")
FONT = os.path.join(ROOT, "work", "patched", "F_FONT.S8")

FULL_ADV, HALF_ADV = 22, 11          # 게임 글자 간격


def load_font():
    data = open(FONT, "rb").read()
    n, codes = font8.codes(data)
    idx = {c: i for i, c in enumerate(codes)}
    return data, idx


def draw_entry(data, idx, entry, args, max_w=760):
    """항목의 텍스트를 줄 단위로 그린다."""
    lines = [[]]
    for kind, v in s8text.lex(entry, args):
        if kind == "nl":
            lines.append([])
        elif kind == "txt":
            lines[-1].append(v)
    rows = []
    for parts in lines:
        b = b"".join(parts)
        canvas = np.full((font8.FULL_H, max_w), 255, dtype=np.uint8)
        x, i = 0, 0
        while i < len(b) and x + FULL_ADV <= max_w:
            c = b[i]
            if s8text.is_lead(c) and i + 1 < len(b):
                code = (c << 8) | b[i + 1]
                if code in idx:
                    g = font8.get_full(data, idx[code])
                    canvas[:, x:x + font8.FULL_W] = np.minimum(
                        canvas[:, x:x + font8.FULL_W], font8.to_gray(g))
                x += FULL_ADV
                i += 2
            else:
                o = font8.HALF_OFS + c * (font8.HALF_W * font8.HALF_H // 2)
                g = font8.decode_4bpp(data[o:o + font8.HALF_W * font8.HALF_H // 2],
                                      font8.HALF_W, font8.HALF_H)
                canvas[:, x:x + font8.HALF_W] = np.minimum(
                    canvas[:, x:x + font8.HALF_W], font8.to_gray(g))
                x += HALF_ADV
                i += 1
        rows.append(canvas)
    return rows


def main():
    out = sys.argv[1]
    targets = [tuple(int(x) for x in a.split(":")) for a in sys.argv[2:]] or [(1, 0), (1, 1)]
    args = units.load_args()
    c = s8text.parse_container(open(MSG, "rb").read())
    data, idx = load_font()
    rows = []
    for g, i in targets:
        rows += draw_entry(data, idx, c.groups[g][i], args)
        rows.append(np.full((6, 760), 200, dtype=np.uint8))
    img = Image.fromarray(np.vstack(rows))
    img.save(out)
    print("저장:", out, img.size)


if __name__ == "__main__":
    main()
