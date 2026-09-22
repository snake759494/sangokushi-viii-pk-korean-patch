# -*- coding: utf-8 -*-
"""무압축 G_*.S8 ([팔레트 1KB x n][8비트 픽셀]) 의 그림 글자를 한국어로 다시 그린다.

글자 상자마다: 원래 글자(주변 바탕보다 밝은 픽셀)를 주변 바탕으로 메우고,
원래 글자 평균색으로 한국어를 그린 뒤 1픽셀 어두운 그림자를 붙인다.
색은 그 상자 안에서 원래 쓰이던 인덱스 중 가장 가까운 것으로 되돌린다.

python tools/gfx_raw.py  -> work/patched/<파일>, work/gfx/prev/raw_<파일>_cmp.png
"""
import os, sys
import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rawgfx
from gfx_main import text_mask, fill_from_ring

W = os.path.normpath(os.path.join(HERE, ".."))

# 파일: (폭, [(x0,y0,x1,y1, 글, 크기)], 반복 x 오프셋들)
JOBS = {
    "G_GUNGI.S8": (1024, [
        (22, 605, 48, 618, "총", 11), (22, 621, 48, 634, "참", 11),
        (283, 594, 303, 604, "공", 10), (309, 594, 329, 604, "수", 10),
        (283, 608, 329, 621, "병사", 12), (283, 622, 329, 636, "부대", 12),
        (44, 640, 97, 657, "전술", 15), (158, 640, 213, 657, "군의", 15),
        (4, 782, 56, 798, "지형", 13),
    ], ((0, 0), (512, 0))),
    "G_GUNGI.S8#big": (1024, [
        (648, 355, 708, 414, "공", 40), (725, 355, 785, 414, "수", 40),
    ], ((0, 0),)),
    "G_WARGRP.S8": (512, [
        (417, 91, 437, 111, "공", 16), (443, 91, 463, 111, "수", 16),
        (412, 117, 462, 141, "병사", 20), (412, 144, 462, 169, "부대", 20),
    ], tuple((0, 256 * k) for k in range(8))),
    # 일기토 화면: 팔레트는 P_IKKI.S8, 밝은 판 위 어두운 글자
    "G_IKBG.S8": (256, [
        (238, 26, 256, 45, "무", 14), (139, 77, 169, 97, "기력", 14),
        (0, 283, 16, 302, "력", 14), (41, 283, 86, 302, "남은 턴", 12),
        (113, 283, 147, 302, "무력", 14), (48, 333, 79, 352, "체력", 14),
        (216, 333, 246, 352, "기력", 14),
    ], ((0, 0),), {"pal": "P_IKKI.S8", "dark": True}),
}


def redraw(img, pal, box, text, size, dark=False):
    x0, y0, x1, y1 = box
    sub = img[y0:y1, x0:x1]
    rgb = pal[sub].astype(np.float32)
    lum = rgb.mean(-1)
    used = np.unique(sub)
    used = used[(pal[used] != [0, 255, 0]).any(1)]
    bgl = np.median(lum)
    glyph = (lum < bgl - 40) if dark else (lum > bgl + 35)
    if not glyph.any():
        print("  글자 없음?", box, text); return
    fg = rgb[glyph].mean(0) * (0.8 if dark else 1.1)
    hole = ndimage.binary_dilation(glyph, iterations=1)
    base = fill_from_ring(rgb, hole)
    h, w = sub.shape
    a = text_mask(text, size, w, h)
    sh = np.zeros_like(a); sh[1:, 1:] = a[:-1, :-1]
    out = base if dark else base * (1 - 0.7 * sh[..., None])
    out = out * (1 - a[..., None]) + np.clip(fg, 0, 255) * a[..., None]
    cand = pal[used].astype(np.float32)
    new = used[((out[..., None, :] - cand[None, None]) ** 2).sum(-1).argmin(-1)]
    img[y0:y1, x0:x1] = new


def main():
    os.makedirs(os.path.join(W, "gfx", "prev"), exist_ok=True)
    os.makedirs(os.path.join(W, "patched"), exist_ok=True)
    files = {}
    for key, job in JOBS.items():
        w, items, offs = job[:3]
        opt = job[3] if len(job) > 3 else {}
        f = key.split("#")[0]
        if f not in files:
            d = open(os.path.join(W, "san8", f), "rb").read()
            n = 0 if "pal" in opt else rawgfx.npal(d)
            px = np.frombuffer(d[n * 1024:], np.uint8)
            h = len(px) // w
            pd = open(os.path.join(W, "san8", opt["pal"]), "rb").read() if "pal" in opt else d
            files[f] = [d, n, w, px[:w * h].reshape(h, w).copy(), px[w * h:].tobytes(), rawgfx.pal(pd, 0)]
        d, n, w, img, tail, pal = files[f]
        for dx, dy in offs:
            for x0, y0, x1, y1, t, s in items:
                redraw(img, pal, (x0 + dx, y0 + dy, x1 + dx, y1 + dy), t, s, opt.get("dark", False))
    for f, (d, n, w, img, tail, pal) in files.items():
        orig = np.frombuffer(d[n * 1024:], np.uint8)[:img.size].reshape(img.shape)
        out = d[:n * 1024] + img.tobytes() + tail
        assert len(out) == len(d)
        open(os.path.join(W, "patched", f), "wb").write(out)
        Image.fromarray(np.concatenate([pal[orig], pal[img]], 1).astype(np.uint8)).save(
            os.path.join(W, "gfx", "prev", "raw_%s_cmp.png" % f))
        print(f, "변경 픽셀", int((orig != img).sum()))


if __name__ == "__main__":
    main()
