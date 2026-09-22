# -*- coding: utf-8 -*-
"""G_SYSTEM.S8 지도 범례(第一~第八, 街道種類·通常·河川·山岳, 委任·内政重視…)를 한국어로.

범례는 8비트(한 줄 256픽셀, 4037~4105줄)이고 팔레트는 같은 파일 0x8400 의 CLUT(PS2 순서)다.
군단 색 견본과 도로 선 견본은 그대로 두고, 글자 칸만 원본 글자가 쓰던 회색 단계 색 번호로 다시 그린다.
gfx_sys4.py 결과(patched/G_SYSTEM.S8) 위에 덧칠한다.
"""
import os, sys
import numpy as np
from scipy import ndimage
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from gfx_main import text_mask
W = os.path.normpath(os.path.join(HERE, ".."))
SRC = os.path.join(W, "san8", "G_SYSTEM.S8")
PATH = os.path.join(W, "patched", "G_SYSTEM.S8")
PAL_OFF = 0x8400
R = [(4037, 4055), (4055, 4071), (4071, 4087), (4087, 4105)]
ITEMS = []
for i, t in enumerate(("제1", "제2", "제3", "제4")):
    ITEMS.append((19, R[i][0], 49, R[i][1], t))
for i, t in enumerate(("제5", "제6", "제7", "제8")):
    ITEMS.append((63, R[i][0], 97, R[i][1], t))
ITEMS += [(100, R[0][0], 173, R[0][1], "도로 종류"),
          (129, R[1][0], 173, R[1][1], "보통"), (129, R[2][0], 173, R[2][1], "하천"),
          (129, R[3][0], 173, R[3][1], "산악"),
          (192, R[0][0], 252, R[0][1], "위임"),
          (192, R[1][0], 252, R[1][1], "내정 중시"), (192, R[2][0], 252, R[2][1], "전쟁 중시"),
          (192, R[3][0], 252, R[3][1], "수송 중시")]
BG = 1


def palette(d):
    i = np.arange(256)
    p = np.frombuffer(d[PAL_OFF:PAL_OFF + 1024], np.uint8).reshape(256, 4)[:, :3]
    return p[(i & 0xE7) | ((i & 0x08) << 1) | ((i & 0x10) >> 1)].astype(np.int32)


def main():
    os.makedirs(os.path.join(W, "gfx", "prev"), exist_ok=True)
    os.makedirs(os.path.join(W, "patched"), exist_ok=True)
    orig_d = open(SRC, "rb").read()
    pal = palette(orig_d)
    d = bytearray(open(PATH, "rb").read())
    rows = (len(d) - 1024) // 256
    im = np.frombuffer(bytes(d[1024:1024 + rows * 256]), np.uint8).reshape(rows, 256).copy()
    orig = np.frombuffer(orig_d[1024:1024 + rows * 256], np.uint8).reshape(rows, 256)
    # 원본 글자 칸이 쓰던 색 번호 = 회색 단계 (견본 색이 칸에 섞이지 않았는지 확인)
    gray = set()
    for x0, y0, x1, y1, _ in ITEMS:
        sub = orig[y0:y1, x0:x1]
        c = pal[sub]
        assert ((c.max(-1) - c.min(-1)) <= 30).all(), ("견본 색이 글자 칸에 걸림", x0, y0)
        gray.update(int(v) for v in np.unique(sub))
    gray = np.array(sorted(gray, key=lambda v: pal[v].mean()))
    glum = pal[gray].mean(-1)
    top = glum.max()
    # 범례 전체에서 원본 글자를 지운다: 색 견본(채도 있는 픽셀 둘레 2칸)과 도로 선 견본만 남김
    ay0, ay1, ax0, ax1 = 4037, 4106, 17, 253
    area = orig[ay0:ay1, ax0:ax1]
    c = pal[area]
    sat = (c.max(-1) - c.min(-1)) > 30
    keep = ndimage.binary_dilation(sat, iterations=2)
    for ly in (4063, 4078, 4093):                  # 通常·河川·山岳 선 견본
        keep[ly - 1 - ay0:ly + 7 - ay0, 101 - ax0:129 - ax0] = True
    blk = im[ay0:ay1, ax0:ax1]
    blk[~keep] = BG
    for x0, y0, x1, y1, t in ITEMS:
        a = text_mask(t, 13, x1 - x0, y1 - y0)
        halo = ndimage.grey_dilation(a, size=(3, 3)) * 0.35
        want = np.maximum(a * top, halo * top * 0.45)
        k = np.abs(want[..., None] - glum[None, None]).argmin(-1)
        m = ~keep[y0 - ay0:y1 - ay0, x0 - ax0:x1 - ax0]
        im[y0:y1, x0:x1][m] = gray[k].astype(np.uint8)[m]
    d[1024:1024 + rows * 256] = im.tobytes()
    open(PATH, "wb").write(bytes(d))
    z = np.concatenate([pal[orig[4030:4110]], pal[im[4030:4110]]], 0).astype(np.uint8)
    Image.fromarray(z).resize((1024, 640), Image.NEAREST).save(os.path.join(W, "gfx", "prev", "legend_cmp.png"))
    print("범례 %d 칸 (회색 단계 %d색) -> %s" % (len(ITEMS), len(gray), PATH))


if __name__ == "__main__":
    main()
