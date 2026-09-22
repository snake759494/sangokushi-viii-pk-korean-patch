# -*- coding: utf-8 -*-
"""G_EMTMP.S8 블록 10 (512x256 8비트, 색 번호 = 밝기): 전략 지도 주(州) 이름 붓글씨 16개를 한국어로.

원본 모양: 첫 글자 크게, 둘째 글자 작게 아래, 흰 글씨 + 오른쪽 아래 회색 그림자.
각 이름의 원래 칸(열 구간·행 범위) 안에만 그린다.
"""
import os, sys, struct
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "title"))
import s9lz  # noqa
from gamedec import game_decode  # noqa
W = os.path.normpath(os.path.join(HERE, ".."))
SRC = os.path.join(W, "san8", "G_EMTMP.S8")
OUT = os.path.join(W, "patched", "G_EMTMP.S8")
FONT = os.path.join(os.path.dirname(W), "SeoulHangangEB.ttf")
BLK, NEXT = 0x2C5A40, 0x2D10F0
NAMES = ["유주", "기주", "청주", "병주", "서주", "연주", "예주", "사예", "옹주", "양주",
         "익주", "남중", "형북", "형남", "회남", "양주"]
SS = 4


def glyph(ch, px, w, h, x, y, canvas):
    f = ImageFont.truetype(FONT, px * SS)
    dr = ImageDraw.Draw(canvas)
    x0, y0, x1, y1 = dr.textbbox((0, 0), ch, font=f)
    dr.text((x * SS + (w * SS - (x1 - x0)) // 2 - x0, y * SS - y0), ch, font=f, fill=255)
    return (y1 - y0) / SS


def main():
    os.makedirs(os.path.join(W, "gfx", "prev"), exist_ok=True)
    os.makedirs(os.path.join(W, "patched"), exist_ok=True)
    d = bytearray(open(SRC, "rb").read())
    t, u, co, lo = struct.unpack_from("<4I", d, BLK)
    raw, info = game_decode(d, BLK, maxout=u + 64)
    img = np.frombuffer(bytes(raw[:u]), np.uint8).reshape(256, 512).copy()
    orig = img.copy()
    m = img > 8
    labels = []
    for (y0, y1) in ((0, 107), (107, 220)):
        cols = np.nonzero(m[y0:y1].any(0))[0]
        segs, s, p = [], cols[0], cols[0]
        for x in cols[1:]:
            if x > p + 1:
                segs.append((s, p)); s = x
            p = x
        segs.append((s, p))
        for (a, b) in segs:
            ys = np.nonzero(m[y0:y1, a:b + 1].any(1))[0]
            labels.append((a, y0 + ys.min(), b + 1, y0 + ys.max() + 1))
    assert len(labels) == 16, len(labels)
    for (x0, y0, x1, y1), name in zip(labels, NAMES):
        w, h = x1 - x0, y1 - y0
        sub_w, sub_h = w - 3, h - 3            # 그림자 자리
        canvas = Image.new("L", (sub_w * SS, sub_h * SS), 0)
        big = int(min(sub_w * 0.95, sub_h * 0.58))
        small = int(min(sub_w * 0.8, sub_h * 0.36))
        glyph(name[0], big, sub_w, sub_h, 0, 0, canvas)
        glyph(name[1], small, sub_w, sub_h, 0, int(sub_h - small * 1.02), canvas)
        a = np.asarray(canvas, np.float32).reshape(sub_h, SS, sub_w, SS).mean((1, 3)) / 255.0
        core = np.zeros((h, w), np.float32); core[:sub_h, :sub_w] = a
        sh = np.zeros_like(core); sh[3:, 3:] = core[:-3, :-3]
        sh = ndimage.gaussian_filter(sh, 1.2) * 0.55
        val = np.maximum(core * 255.0, sh * 255.0 * (1 - core))
        img[y0:y1, x0:x1] = np.clip(np.rint(val), 0, 255).astype(np.uint8)
    blob = s9lz.encode_best(img.tobytes(), types=(0, 1, 2, 3))
    chk, _ = game_decode(blob, 0, maxout=u + 64)
    assert bytes(chk[:u]) == img.tobytes()
    slot = NEXT - BLK
    if len(blob) > slot:
        raise SystemExit("블록이 자리보다 큼 %d > %d" % (len(blob), slot))
    d[BLK:BLK + slot] = blob + bytes(slot - len(blob))
    open(OUT, "wb").write(bytes(d))
    Image.fromarray(np.concatenate([orig, img], 0)).save(os.path.join(W, "gfx", "prev", "emtmp10_cmp.png"))
    print("주 이름 16개: %d / %d 바이트 -> %s" % (len(blob), slot, OUT))


if __name__ == "__main__":
    main()
