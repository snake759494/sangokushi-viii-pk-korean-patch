# -*- coding: utf-8 -*-
"""G_SYSTEM.S8 전략 지도 범례(第一~第八, 街道種類·通常·河川·山岳, 委任·内政重視…)를 한국어로.

범례는 8비트(한 줄 256픽셀)지만 알맞은 팔레트를 찾지 못했으므로 인덱스 공간에서 작업한다:
바탕 인덱스(1) 위의 글자 픽셀 인덱스들을 '획 안쪽 정도'(주변 8칸 중 글자 칸 비율)로 줄 세우고,
새 글자의 알파가 클수록 안쪽 인덱스를 쓴다. gfx_sys4.py 결과(patched/G_SYSTEM.S8) 위에 덧칠한다.
"""
import os, sys
import numpy as np
from scipy import ndimage
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from gfx_main import text_mask
W = os.path.normpath(os.path.join(HERE, ".."))
PATH = os.path.join(W, "patched", "G_SYSTEM.S8")
R = [(4037, 4055), (4055, 4071), (4071, 4087), (4087, 4105)]
ITEMS = []
for i, t in enumerate(("제1", "제2", "제3", "제4")):
    ITEMS.append((18, R[i][0], 52, R[i][1], t))
for i, t in enumerate(("제5", "제6", "제7", "제8")):
    ITEMS.append((62, R[i][0], 96, R[i][1], t))
ITEMS += [(100, R[0][0], 176, R[0][1], "도로 종류"),
          (128, R[1][0], 176, R[1][1], "보통"), (128, R[2][0], 176, R[2][1], "하천"),
          (128, R[3][0], 176, R[3][1], "산악"),
          (190, R[0][0], 252, R[0][1], "위임"),
          (190, R[1][0], 252, R[1][1], "내정 중시"), (190, R[2][0], 252, R[2][1], "전쟁 중시"),
          (190, R[3][0], 252, R[3][1], "수송 중시")]
BG = 1


def main():
    os.makedirs(os.path.join(W, "gfx", "prev"), exist_ok=True)
    os.makedirs(os.path.join(W, "patched"), exist_ok=True)
    d = bytearray(open(PATH, "rb").read())
    rows = (len(d) - 1024) // 256
    im = np.frombuffer(bytes(d[1024:1024 + rows * 256]), np.uint8).reshape(rows, 256).copy()
    before = im.copy()
    # 인덱스별 '안쪽 정도'
    reg = before[4037:4106, 18:252]
    fgm = reg != BG
    inner = ndimage.uniform_filter(fgm.astype(np.float32), 3)
    score = {}
    for v in np.unique(reg[fgm]):
        score[int(v)] = float(inner[reg == v].mean())
    ramp = sorted(score, key=score.get)            # 가장자리 -> 안쪽
    for x0, y0, x1, y1, t in ITEMS:
        sub = im[y0:y1, x0:x1]
        a = text_mask(t, 13, x1 - x0, y1 - y0)
        a = np.maximum(a, 0.3 * ndimage.grey_dilation(a, size=(3, 3)))   # 원본처럼 옅은 번짐
        new = np.full(sub.shape, BG, np.uint8)
        on = a > 0.08
        k = np.clip((a * (len(ramp) - 1)).round().astype(int), 0, len(ramp) - 1)
        new[on] = np.array(ramp, np.uint8)[k[on]]
        im[y0:y1, x0:x1] = new
    d[1024:1024 + rows * 256] = im.tobytes()
    open(PATH, "wb").write(bytes(d))
    z = np.concatenate([before[4030:4110], im[4030:4110]], 0)
    lum = np.zeros(256); lum[ramp] = np.linspace(80, 255, len(ramp)); lum[BG] = 0
    Image.fromarray(lum[z].astype(np.uint8)).resize((1024, 640), Image.NEAREST).save(
        os.path.join(W, "gfx", "prev", "legend_cmp.png"))
    print("범례", len(ITEMS), "칸 ->", PATH)


if __name__ == "__main__":
    main()
