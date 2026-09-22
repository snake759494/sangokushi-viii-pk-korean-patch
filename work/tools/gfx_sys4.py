# -*- coding: utf-8 -*-
"""G_SYSTEM.S8 의 4비트 아이콘(委·指·総·参·行·金)을 한국어로 다시 그린다.

G_SYSTEM = [팔레트 1KB][픽셀]. 아이콘 영역은 4비트(바이트당 2픽셀, 낮은 니블 = 왼쪽), 한 줄 256바이트 = 512픽셀.
아이콘 팔레트는 니블 값이 곧 밝기 순서라서 니블 공간에서 직접 칠한다.
입력은 work/patched/G_SYSTEM.S8 가 있으면 그것(다른 단계 결과 위에 덧칠), 없으면 원본.
"""
import os, sys
import numpy as np
from PIL import Image
from scipy import ndimage
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from gfx_main import text_mask
W = os.path.normpath(os.path.join(HERE, ".."))
SRC = os.path.join(W, "san8", "G_SYSTEM.S8")
OUT = os.path.join(W, "patched", "G_SYSTEM.S8")

# (x0, y0, x1, y1 : 4비트 픽셀 좌표, 글, 크기, 어두운 글자?)
ICONS = [
    (72, 340, 96, 364, "위", 18, False), (72, 364, 96, 388, "지", 18, False),
    (72, 388, 96, 412, "총", 18, True), (72, 412, 96, 436, "참", 18, True),
    (96, 220, 120, 244, "행", 18, True), (96, 364, 120, 388, "금", 18, True),
    (268, 6087, 380, 6117, "정 보", 22, False),        # 전투 화면 안내판 □情報
    # 부대 종류 표시 正·増·応·放 (정규군·증원군·응원군·방랑군), 두 벌
    (461, 197, 479, 215, "정", 14, False),
    (481, 197, 499, 215, "정", 14, False),
    (461, 217, 479, 235, "증", 14, False),
    (481, 217, 499, 235, "증", 14, False),
    (461, 237, 479, 255, "응", 14, False),
    (481, 237, 499, 255, "응", 14, False),
    (461, 257, 479, 275, "방", 14, False),
    (481, 257, 499, 275, "방", 14, False),
]


TAGS = ("정", "증", "응", "방")
FLAT = ("위", "지", "행", "금", "정 보", "정", "증", "응", "방")


def main():
    os.makedirs(os.path.join(W, "gfx", "prev"), exist_ok=True)
    os.makedirs(os.path.join(W, "patched"), exist_ok=True)
    d = bytearray(open(SRC, "rb").read())
    base = 1024
    rows = (len(d) - base) // 256
    b = np.frombuffer(bytes(d[base:base + rows * 256]), np.uint8).reshape(rows, 256)
    q = np.zeros((rows, 512), np.uint8); q[:, 0::2] = b & 15; q[:, 1::2] = b >> 4
    before = q.copy()
    for x0, y0, x1, y1, t, size, dark in ICONS:
        m = 1 if t in TAGS else 3                       # 테두리는 그대로
        sub = q[y0 + m:y1 - m, x0 + m:x1 - m].astype(np.float32)
        ring = np.concatenate([sub[0], sub[-1], sub[:, 0], sub[:, -1]]).astype(int)
        bg = float(np.bincount(ring).argmax()) if t in FLAT else float(np.median(sub))
        glyph = (sub < bg - 2) if dark else (sub > bg + 2)
        fg = sub[glyph].min() if dark else sub[glyph].max()
        hole = ndimage.binary_dilation(glyph, iterations=1)
        idx = ndimage.distance_transform_edt(hole, return_distances=False, return_indices=True)
        filled = np.where(hole, sub[idx[0], idx[1]], sub)
        filled = np.where(hole, bg, filled)
        if t in FLAT:                                   # 무늬 없는 바탕은 통째로 비운다
            filled[:] = bg
        h, w = sub.shape
        a = text_mask(t, size, w, h)
        out = filled + (fg - filled) * a
        q[y0 + m:y1 - m, x0 + m:x1 - m] = np.clip(np.rint(out), 0, 15).astype(np.uint8)
    nb = (q[:, 0::2] | (q[:, 1::2] << 4)).astype(np.uint8)
    d[base:base + rows * 256] = nb.tobytes()
    open(OUT, "wb").write(bytes(d))
    Image.fromarray(np.concatenate([before[6080:6125, 180:400], q[6080:6125, 180:400]], 0) * 17).resize(
        (880, 360), Image.NEAREST).save(os.path.join(W, "gfx", "prev", "sys4_info.png"))
    Image.fromarray(np.concatenate([before[195:280, 455:500], q[195:280, 455:500]], 1) * 17).resize(
        (450, 425), Image.NEAREST).save(os.path.join(W, "gfx", "prev", "sys4_tags.png"))
    z = np.concatenate([before[200:440, 60:130], q[200:440, 60:130]], 1) * 17
    Image.fromarray(z).resize((140 * 4, 240 * 4), Image.NEAREST).save(os.path.join(W, "gfx", "prev", "sys4_cmp.png"))
    print("G_SYSTEM 아이콘", len(ICONS), "개 ->", OUT)


if __name__ == "__main__":
    main()
