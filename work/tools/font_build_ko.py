# -*- coding: utf-8 -*-
"""F_FONT.S8 의 한자 슬롯(亜=SJIS 889F, 인덱스 340)에 KS X 1001 한글 2,350자를 입힌다.

출력 work/patched/F_FONT.S8, work/font_ko/hangul.tbl, 미리보기 PNG
"""
import os, struct, sys
import numpy as np
from PIL import Image, ImageFont, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import font8

ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
SRC = os.path.join(ROOT, "work", "san8", "F_FONT.S8")
TTF = os.path.join(ROOT, "SeoulHangangB.ttf")
OUT_FONT = os.path.join(ROOT, "work", "patched", "F_FONT.S8")
OUT_DIR = os.path.join(ROOT, "work", "font_ko")

START_INDEX, START_CODE = 340, 0x889F
# 게임은 24x24 셀을 2행째부터 그린다(원본 한자도 2행에서 시작한다).
# 0~1행에 획이 있으면 그 획이 잘리고, 대신 다음 글자의 0~1행이 한 칸 아래에
# 점처럼 따라 나온다. 그래서 한글도 2행~23행 안에 들어가게 베이스라인을 잡는다.
FONT_SIZE, BASELINE, CENTER_X, PAD = 22, 21, 10.5, 16
TOP_MARGIN = 2               # 이 행 위로는 획이 없어야 한다


def ksx1001_hangul():
    return [bytes([hi, lo]).decode("euc-kr") for hi in range(0xB0, 0xC9) for lo in range(0xA1, 0xFF)]


def render(font, ch):
    size = font8.FULL_W + PAD * 2
    im = Image.new("L", (size, size), 0)
    ImageDraw.Draw(im).text((PAD, PAD + BASELINE), ch, font=font, fill=255, anchor="ls")
    a = np.asarray(im)
    cols = np.nonzero(a.max(axis=0))[0]
    x0, x1 = int(cols[0]), int(cols[-1])
    left = int(round(CENTER_X - (x1 - x0) / 2.0))
    out = np.zeros((font8.FULL_H, font8.FULL_W), dtype=np.uint8)
    w = x1 - x0 + 1
    src = a[PAD:PAD + font8.FULL_H, x0:x1 + 1]
    lo, hi = max(0, -left), min(w, font8.FULL_W - left)
    out[:, left + lo:left + hi] = src[:, lo:hi]
    clipped = int(a.sum()) != int(out.astype(np.int64).sum())
    rows = np.nonzero(out.max(axis=1))[0]
    high = bool(len(rows)) and int(rows[0]) < TOP_MARGIN     # 2행 위로 삐져나감
    return ((out.astype(np.int32) * 15 + 127) // 255).astype(np.uint8), clipped, high


def main():
    data = bytearray(open(SRC, "rb").read())
    n, codes = font8.codes(data)
    hangul = ksx1001_hangul()
    assert len(hangul) == 2350
    assert codes[START_INDEX] == START_CODE, "시작 슬롯이 亜(889F)가 아님"
    assert START_INDEX + len(hangul) <= n

    font = ImageFont.truetype(TTF, FONT_SIZE)
    clipped, highs = [], []
    for k, ch in enumerate(hangul):
        g, clip, high = render(font, ch)
        if clip:
            clipped.append(ch)
        if high:
            highs.append(ch)
        o = font8.FULL_OFS + (START_INDEX + k) * font8.GLYPH_BYTES
        data[o:o + font8.GLYPH_BYTES] = font8.encode_4bpp(g)

    os.makedirs(os.path.dirname(OUT_FONT), exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)
    open(OUT_FONT, "wb").write(bytes(data))
    with open(os.path.join(OUT_DIR, "hangul.tbl"), "w", encoding="utf-8", newline="\n") as f:
        for k, ch in enumerate(hangul):
            f.write("%04X=%s\n" % (codes[START_INDEX + k], ch))

    full = [font8.get_full(data, i) for i in range(n)]
    Image.fromarray(font8.pack_sheet(full, font8.FULL_W, font8.FULL_H, font8.SHEET_COLS)).save(
        os.path.join(OUT_DIR, "font_full_24x24.png"))
    idx = list(range(START_INDEX, START_INDEX + 300))
    font8.preview_sheet([full[i] for i in idx], idx, font8.FULL_W, font8.FULL_H, 50).save(
        os.path.join(OUT_DIR, "hangul_sheet.png"))

    slot = {ch: START_INDEX + k for k, ch in enumerate(hangul)}
    lines = ["유비는 관우, 장비와 도원에서 의형제를 맺었다.",
             "조조가 대군을 이끌고 적벽으로 향했습니다!",
             "가나다라마바사아자차카타파하 뷁쀍똠방각하"]
    canvas = np.full((len(lines) * font8.FULL_H, 30 * font8.FULL_W), 255, dtype=np.uint8)
    for r, line in enumerate(lines):
        for c, ch in enumerate(line[:30]):
            if ch in slot:
                canvas[r*font8.FULL_H:(r+1)*font8.FULL_H, c*font8.FULL_W:(c+1)*font8.FULL_W] = font8.to_gray(full[slot[ch]])
    im = Image.fromarray(canvas)
    im.resize((im.size[0]*2, im.size[1]*2), Image.NEAREST).save(os.path.join(OUT_DIR, "preview.png"))

    last = START_INDEX + len(hangul) - 1
    print("한글 %d자: 인덱스 %d~%d, SJIS %04X~%04X" % (len(hangul), START_INDEX, last, codes[START_INDEX], codes[last]))
    print("셀 밖으로 잘린 글자 %d개 %s" % (len(clipped), "".join(clipped[:40])))
    print("윗 %d행을 침범한 글자 %d개 %s" % (TOP_MARGIN, len(highs), "".join(highs[:40])))
    print("출력:", OUT_FONT, os.path.getsize(OUT_FONT), "B")


if __name__ == "__main__":
    sys.exit(main())
