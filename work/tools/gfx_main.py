# -*- coding: utf-8 -*-
"""G_MAIN.S8 의 그림 글자(조작 안내판 情報/進行/地図, 신분 배지 君主…, 戦/特/行/金 표식)를 한국어로 다시 그린다.

형식: 블록 = 9PK 와 같은 KOEI LZSS. 블록 0 = 512x256 8비트, 블록 1·2 = 256x256 8비트.
팔레트: 블록 2 뒤(0x24310)에 1KB RGBA 팔레트 7개, PS2 CLUT 순서(인덱스 비트 3·4 교환).
방법: 팔레트 0 으로 RGB 로 풀어 글자 상자를 지우고(주변 배경으로 메움) 한국어를 그린 뒤,
      그 상자 안에 원래 쓰이던 인덱스 중 가장 가까운 색으로 되돌린다(다른 팔레트 상태에서도 같은 명암 단계가 되도록).

python tools/gfx_main.py   -> work/patched/G_MAIN.S8, work/gfx/prev/main_*.png
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
SRC = os.path.join(W, "san8", "G_MAIN.S8")
OUT = os.path.join(W, "patched", "G_MAIN.S8")
PREV = os.path.join(W, "gfx", "prev")
FONT = os.path.join(os.path.dirname(W), "SeoulHangangEB.ttf")
PAL_OFF = 0x24310
SS = 4                                  # 초과 표본(안티에일리어싱)

# (블록, 상자 x0,y0,x1,y1, 글, 글자 크기, 모양)  모양: badge = 흰 글자+어두운 테두리, panel = 검은 바탕 위 밝은 글자
ITEMS = [
    (0, (70, 137, 116, 159), "군주", 16, "badge"), (0, (117, 137, 162, 159), "일반", 16, "badge"),
    (0, (70, 161, 116, 183), "도독", 16, "badge"), (0, (117, 161, 162, 183), "두령", 16, "badge"),
    (0, (70, 185, 116, 207), "태수", 16, "badge"), (0, (117, 185, 162, 207), "동지", 16, "badge"),
    (0, (70, 209, 116, 231), "군사", 16, "badge"), (0, (117, 209, 162, 231), "재야", 16, "badge"),
    (0, (100, 4, 160, 29), "정보", 20, "panel"), (0, (100, 31, 160, 55), "진행", 20, "panel"),
    (0, (100, 56, 160, 81), "지도", 20, "panel"),
    (0, (195, 4, 256, 29), "정보", 20, "panel"), (0, (195, 31, 256, 55), "휴양", 20, "panel"),
    (0, (195, 56, 256, 81), "지도", 20, "panel"),
]
ROUND = [  # 동그란 표식 한 글자: (블록, 중심 x, y, 반지름 안쪽, 글)
    (0, 18, 213, 10, "전"), (0, 50, 213, 10, "특"),
]


def palette(d, k=0):
    i = np.arange(256)
    j = (i & 0xE7) | ((i & 0x08) << 1) | ((i & 0x10) >> 1)
    p = np.frombuffer(d[PAL_OFF + k * 1024:PAL_OFF + (k + 1) * 1024], np.uint8).reshape(256, 4)
    return p[j][:, :3].astype(np.int32)


def blocks(d, n=3):
    res, o = [], 0
    for _ in range(n):
        t, u, co, lo = struct.unpack_from("<4I", d, o)
        out, info = game_decode(d, o, maxout=u + 64)
        end = o + max(info["lits_end"], info["end_code_at"] + 2)
        res.append([o, t, u, end, bytearray(out[:u])])
        o = (end + 15) & ~15
    return res


def text_mask(text, size, w, h):
    f = ImageFont.truetype(FONT, size * SS)
    im = Image.new("L", (w * SS, h * SS), 0)
    dr = ImageDraw.Draw(im)
    x0, y0, x1, y1 = dr.textbbox((0, 0), text, font=f)
    dr.text(((w * SS - (x1 - x0)) // 2 - x0, (h * SS - (y1 - y0)) // 2 - y0), text, font=f, fill=255)
    a = np.asarray(im, np.float32).reshape(h, SS, w, SS).mean((1, 3)) / 255.0
    return a


def fill_from_ring(rgb, hole):
    idx = ndimage.distance_transform_edt(hole, return_distances=False, return_indices=True)
    out = rgb[idx[0], idx[1]]
    sm = ndimage.uniform_filter(out.astype(np.float32), size=(3, 3, 1))
    out = np.where(hole[..., None], sm, rgb)
    return out


def redraw(img, pal, box, text, size, style):
    x0, y0, x1, y1 = box
    sub = img[y0:y1, x0:x1]
    used = np.unique(sub)
    used = used[(pal[used] != [0, 255, 0]).any(1)]
    rgb = pal[sub].astype(np.float32)
    h, w = sub.shape
    a = text_mask(text, size, w, h)
    if style == "panel":
        base = rgb.copy()
        base[:] = pal[np.bincount(sub.ravel()).argmax()]
        out = base * (1 - a[..., None]) + np.array([232, 232, 232]) * a[..., None]
    else:
        # 배지 가장자리(투명·테두리)는 그대로 두고 안쪽 글자 자리만 새로 칠한다
        shape = (pal[sub] != [0, 255, 0]).any(-1)
        inner = ndimage.binary_erosion(shape, iterations=3)
        lum = rgb.mean(-1)
        hole = inner & ndimage.binary_dilation((lum > 140) | (lum < 50), iterations=1)
        base = fill_from_ring(rgb, hole)
        outline = ndimage.grey_dilation(a, size=(3, 3))
        out = base * (1 - outline[..., None]) + np.array([30, 20, 35]) * outline[..., None]
        out = out * (1 - a[..., None]) + np.array([250, 250, 250]) * a[..., None]
        keep = ~ndimage.binary_erosion(shape, iterations=2)
        out = np.where(keep[..., None], rgb, out)
    # 가장 가까운 인덱스(상자 안에서 쓰이던 것만)
    cand = pal[used].astype(np.float32)
    dist = ((out[..., None, :] - cand[None, None]) ** 2).sum(-1)
    new = used[dist.argmin(-1)].astype(np.uint8)
    img[y0:y1, x0:x1] = new


def redraw_round(img, pal, cx, cy, r, text):
    box = (cx - r, cy - r, cx + r + 1, cy + r + 1)
    x0, y0, x1, y1 = box
    sub = img[y0:y1, x0:x1]
    yy, xx = np.mgrid[y0:y1, x0:x1]
    disk = (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r
    rgb = pal[sub].astype(np.float32)
    lum = rgb.mean(-1)
    used = np.unique(sub[disk])
    # 원 안의 배경색 = 원 안 중간 밝기 픽셀 평균
    mid = disk & (lum > 60) & (lum < 170)
    bgc = rgb[mid].mean(0) if mid.any() else rgb[disk].mean(0)
    base = rgb.copy()
    base[disk] = bgc
    a = text_mask(text, 2 * r - 2, x1 - x0, y1 - y0)
    outline = ndimage.grey_dilation(a, size=(3, 3))
    out = base * (1 - outline[..., None]) + np.array([30, 20, 35]) * outline[..., None]
    out = out * (1 - a[..., None]) + np.array([250, 250, 250]) * a[..., None]
    out = np.where(disk[..., None], out, rgb)
    cand = pal[used].astype(np.float32)
    dist = ((out[..., None, :] - cand[None, None]) ** 2).sum(-1)
    new = used[dist.argmin(-1)].astype(np.uint8)
    img[y0:y1, x0:x1] = np.where(disk, new, sub)


def main():
    os.makedirs(os.path.join(W, "gfx", "prev"), exist_ok=True)
    os.makedirs(os.path.join(W, "patched"), exist_ok=True)
    d = open(SRC, "rb").read()
    pal = palette(d, 0)
    pal3 = palette(d, 3)                # 안내판은 회색조 팔레트 3 으로 그려진다
    bl = blocks(d)
    shapes = {0: (256, 512), 1: (256, 256), 2: (256, 256)}
    imgs = {k: np.frombuffer(bytes(bl[k][4]), np.uint8).reshape(shapes[k]).copy() for k in range(3)}
    before = {k: v.copy() for k, v in imgs.items()}
    for blk, box, text, size, style in ITEMS:
        redraw(imgs[blk], pal3 if style == "panel" else pal, box, text, size, style)
    for blk, cx, cy, r, text in ROUND + EXTRA_ROUND:
        redraw_round(imgs[blk], pal, cx, cy, r, text)
    out = bytearray(d)
    for k in range(3):
        if (imgs[k] == before[k]).all():
            continue
        o, t, u, end, _ = bl[k]
        slot = (bl[k + 1][0] if k < 2 else PAL_OFF) - o
        blob = s9lz.encode_best(imgs[k].tobytes(), types=(0, 1, 2, 3))
        chk, info = game_decode(blob, 0, maxout=u + 64)
        assert bytes(chk[:u]) == imgs[k].tobytes()
        if len(blob) > slot:
            raise SystemExit("블록 %d 가 자리보다 큼 %d > %d" % (k, len(blob), slot))
        out[o:o + slot] = blob + bytes(slot - len(blob))
        print("블록 %d: %d / %d 바이트" % (k, len(blob), slot))
        for pk in (0, 3):
            pp = palette(d, pk)
            Image.fromarray(np.concatenate([pp[before[k]], pp[imgs[k]]], 1).astype(np.uint8)).resize(
                (shapes[k][1] * 4, shapes[k][0] * 2), Image.NEAREST).save(os.path.join(PREV, "main_%d_p%d.png" % (k, pk)))
    # 업무 명령·결과 판 (블록 12·13)
    epal = np.frombuffer(d[EMB_PAL:EMB_PAL + 1024], np.uint8).reshape(256, 4)
    i = np.arange(256)
    epal = epal[(i & 0xE7) | ((i & 0x08) << 1) | ((i & 0x10) >> 1)][:, :3].astype(np.int32)
    for k, (o, slot_end) in EMB_BLOCKS.items():
        t, u, co, lo = struct.unpack_from("<4I", d, o)
        raw, info = game_decode(d, o, maxout=u + 64)
        img = np.frombuffer(bytes(raw[:u]), np.uint8).reshape(-1, 256).copy()
        orig = img.copy()
        for blk, box, text, size in EMB:
            if blk == k:
                redraw_emb(img, epal, box, text, size)
        blob = s9lz.encode_best(img.tobytes(), types=(0, 1, 2, 3))
        chk, info = game_decode(blob, 0, maxout=u + 64)
        assert bytes(chk[:u]) == img.tobytes()
        slot = slot_end - o
        if len(blob) > slot:
            raise SystemExit("블록 %d 가 자리보다 큼 %d > %d" % (k, len(blob), slot))
        out[o:o + slot] = blob + bytes(slot - len(blob))
        print("블록 %d: %d / %d 바이트" % (k, len(blob), slot))
        Image.fromarray(np.concatenate([epal[orig[200:780]], epal[img[200:780]]], 1).astype(np.uint8)).resize(
            (1024, 1160), Image.NEAREST).save(os.path.join(PREV, "main_%d_emb.png" % k))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "wb").write(out)
    print("->", OUT)


# 업무 명령·결과 화면 조각 판(블록 13·12, 256폭 타일, 팔레트는 0x20B848 의 17번)의 새김 글자
EMB_PAL = 0x20B848 + 1024 * 17
EMB_BLOCKS = {12: (0x17A860, 0x1C3D50), 13: (0x1C3D50, 0x20B845)}   # 블록 위치, 다음 자료 시작
EMB = [
    (13, (78, 221, 130, 247), "무장", 20), (13, (155, 221, 207, 247), "업무", 20), (13, (237, 221, 256, 247), "목", 20),
    (13, (13, 447, 110, 472), "업무 명령", 20),
    (13, (3, 475, 30, 500), "표", 20), (13, (95, 475, 147, 500), "무장", 20), (13, (173, 475, 224, 500), "업무", 20),
    (13, (0, 734, 47, 759), "목표", 20),
    (12, (108, 221, 160, 247), "무장", 20), (12, (188, 221, 240, 247), "업무", 20),
    (12, (13, 447, 110, 472), "업무 결과", 20),
    (12, (0, 475, 47, 500), "달성", 20), (12, (126, 475, 178, 500), "무장", 20), (12, (203, 475, 254, 500), "업무", 20),
    (12, (3, 734, 62, 759), "달성", 20),
]


def redraw_emb(img, pal, box, text, size):
    """새김 글자: 밝은 획 + 오른쪽 아래 어두운 그림자."""
    x0, y0, x1, y1 = box
    sub = img[y0:y1, x0:x1]
    rgb = pal[sub].astype(np.float32)
    lum = rgb.mean(-1)
    key = (pal[sub] == [0, 255, 0]).all(-1)
    used = np.unique(sub[~key])
    med = ndimage.median_filter(lum, size=9)
    glyph = (lum > med + 14) | (lum < med - 22)
    glyph &= ~key
    hole = glyph & ~key
    base = fill_from_ring(rgb, hole)
    hi = rgb[(lum > med + 14) & ~key]
    lo = rgb[(lum < med - 22) & ~key]
    if len(hi):
        hl = hi.mean(-1)
        fg = hi[hl >= np.percentile(hl, 70)].mean(0)
    else:
        fg = rgb.mean((0, 1)) * 1.25
    if len(lo):
        ll = lo.mean(-1)
        sc = lo[ll <= np.percentile(ll, 40)].mean(0)
    else:
        sc = rgb.mean((0, 1)) * 0.6
    h, w = sub.shape
    a = text_mask(text, size, w, h)
    sh = np.zeros_like(a); sh[1:, 1:] = a[:-1, :-1]
    sh = np.clip(sh - a, 0, 1)
    out = base * (1 - sh[..., None]) + sc * sh[..., None]
    out = out * (1 - a[..., None]) + fg * a[..., None]
    out = np.where(key[..., None], rgb, out)
    cand = pal[used].astype(np.float32)
    new = used[((out[..., None, :] - cand[None, None]) ** 2).sum(-1).argmin(-1)]
    img[y0:y1, x0:x1] = np.where(key, sub, new)


EXTRA_ROUND = [(1, 55, 174, 10, "행"), (2, 55, 174, 10, "행"), (2, 28, 200, 10, "금")]

if __name__ == "__main__":
    main()
