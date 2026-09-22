# -*- coding: utf-8 -*-
"""G_WARGRP.S8 전투 스프라이트(4비트 부분)의 그림 글자를 한국어로.

- 부대 상태 표시 挑発·委中·指中 -> 도발·위임·지시 : 테두리·바탕·글자·그림자 네 값만 쓰는 2색 글자
- 총대장·참모 표시 総·参 (두 벌) -> 총·참 : 명암 단계(바탕 5, 밝은 획 f, 어두운 가장자리 2)
4비트 영역: 팔레트 9개(9KB) 뒤 한 줄 256바이트 = 512픽셀, 낮은 니블이 왼쪽.
gfx_raw.py 가 만든 work/patched/G_WARGRP.S8 위에 덧칠한다.
"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
W = os.path.normpath(os.path.join(HERE, ".."))
PATH = os.path.join(W, "patched", "G_WARGRP.S8")
BASE = 9 * 1024
FONT_TAG = os.path.join(os.path.dirname(W), "NanumSquareNeo-cBd.ttf")
FONT_ICON = os.path.join(os.path.dirname(W), "SeoulHangangEB.ttf")

# (x0, x1 : 태그 바깥 테두리 포함 가로 범위, 바탕, 글자, 글)
TAGS = [(144, 179, 0x7, 0xE, "도발"), (180, 215, 0x9, 0xF, "위임"), (216, 251, 0xA, 0xE, "지시")]
TAG_Y = (7690, 7703)          # 안쪽 행 범위 (위아래 테두리 제외)
# (x0, y0, x1, y1 : 안쪽 칸, 글)
ICONS = [(418, 7658, 438, 7678, "총"), (442, 7658, 462, 7678, "참"),
         (418, 7682, 438, 7702, "총"), (442, 7682, 462, 7702, "참")]


def mask(text, font, size, w, h, ss=4, dx=0, dy=0):
    f = ImageFont.truetype(font, size * ss)
    im = Image.new("L", (w * ss, h * ss), 0)
    dr = ImageDraw.Draw(im)
    x0, y0, x1, y1 = dr.textbbox((0, 0), text, font=f)
    dr.text(((w * ss - (x1 - x0)) // 2 - x0 + dx * ss, (h * ss - (y1 - y0)) // 2 - y0 + dy * ss),
            text, font=f, fill=255)
    return np.asarray(im, np.float32).reshape(h, ss, w, ss).mean((1, 3)) / 255.0


def main():
    os.makedirs(os.path.join(W, "gfx", "prev"), exist_ok=True)
    os.makedirs(os.path.join(W, "patched"), exist_ok=True)
    d = bytearray(open(PATH, "rb").read())
    rows = (len(d) - BASE) // 256
    b = np.frombuffer(bytes(d[BASE:BASE + rows * 256]), np.uint8).reshape(rows, 256)
    q = np.zeros((rows, 512), np.uint8); q[:, 0::2] = b & 15; q[:, 1::2] = b >> 4
    before = q.copy()
    y0, y1 = TAG_Y
    for x0, x1, fill, fg, text in TAGS:
        sub = q[y0:y1, x0:x1]
        inner = np.isin(sub, (fill, fg, 1))
        # 테두리 안쪽만: 가로로 테두리 값 사이에 있는 칸
        for r in range(sub.shape[0]):
            cols = np.nonzero(~np.isin(sub[r], (fill, fg, 1, 0)))[0]
            if len(cols) >= 2:
                inner[r, :cols[0] + 1] = False
                inner[r, cols[-1]:] = False
        ys, xs = np.nonzero(inner)
        iy0, iy1, ix0, ix1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        h, w = iy1 - iy0, ix1 - ix0
        a = mask(text, FONT_TAG, 10, w, h) > 0.35
        sh = np.zeros_like(a)
        sh[1:, :] |= a[:-1, :]; sh[:, 1:] |= a[:, :-1]
        new = np.full((h, w), fill, np.uint8)
        new[sh & ~a] = 1
        new[a] = fg
        blk = sub[iy0:iy1, ix0:ix1]
        m = inner[iy0:iy1, ix0:ix1]
        blk[m] = new[m]
    for x0, y0_, x1, y1_, text in ICONS:
        h, w = y1_ - y0_, x1 - x0
        a = mask(text, FONT_ICON, 17, w, h)
        s = np.zeros_like(a); s[1:, 1:] = a[:-1, :-1]
        s = np.clip(s - a, 0, 1)
        out = 5.0 - 3.0 * s
        out = out + (15.0 - out) * a
        q[y0_:y1_, x0:x1] = np.clip(np.rint(out), 0, 15).astype(np.uint8)
    nb = (q[:, 0::2] | (q[:, 1::2] << 4)).astype(np.uint8)
    d[BASE:BASE + rows * 256] = nb.tobytes()
    open(PATH, "wb").write(bytes(d))
    z = np.concatenate([before[7650:7706, 140:470], q[7650:7706, 140:470]], 0) * 17
    Image.fromarray(z.astype(np.uint8)).resize((330 * 4, 112 * 4), Image.NEAREST).save(
        os.path.join(W, "gfx", "prev", "wargrp4_cmp.png"))
    print("G_WARGRP 4비트: 태그 %d, 아이콘 %d -> %s" % (len(TAGS), len(ICONS), PATH))


if __name__ == "__main__":
    main()
