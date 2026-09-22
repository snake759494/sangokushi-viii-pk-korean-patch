# -*- coding: utf-8 -*-
"""F_FONT.S8 글꼴 구조 공통 코드.

0x00000  u32    전각 글리프 수 N (=3759)
0x00004  u16[N] 글리프의 Shift-JIS 코드
0x01D64  반각 256자 : 12x24 4bpp (144 B)
0x0AD64  전각 N자   : 24x24 4bpp (288 B)
4bpp: 하위 니블이 왼쪽 픽셀, 0(투명)~15(진함)
"""
import struct
import numpy as np
from PIL import Image, ImageDraw

HALF_OFS, HALF_W, HALF_H, HALF_N = 0x1D64, 12, 24, 256
FULL_OFS, FULL_W, FULL_H = 0xAD64, 24, 24
GLYPH_BYTES = FULL_W * FULL_H // 2
SHEET_COLS = 64


def codes(data):
    n = struct.unpack_from("<I", data, 0)[0]
    return n, list(struct.unpack_from("<%dH" % n, data, 4))


def decode_4bpp(buf, w, h):
    b = np.frombuffer(buf, dtype=np.uint8)
    px = np.empty(w * h, dtype=np.uint8)
    px[0::2] = b & 0x0F
    px[1::2] = b >> 4
    return px.reshape(h, w)


def encode_4bpp(g):
    p = g.reshape(-1)
    return ((p[0::2] & 0x0F) | (p[1::2] << 4)).astype(np.uint8).tobytes()


def to_gray(g):
    return (255 - g.astype(np.int32) * 17).astype(np.uint8)


def pack_sheet(glyphs, w, h, cols):
    rows = (len(glyphs) + cols - 1) // cols
    sheet = np.full((rows * h, cols * w), 255, dtype=np.uint8)
    for i, g in enumerate(glyphs):
        r, c = divmod(i, cols)
        sheet[r * h:(r + 1) * h, c * w:(c + 1) * w] = to_gray(g)
    return sheet


def preview_sheet(glyphs, labels, w, h, cols, scale=2):
    cell_w, cell_h = w * scale + 2, h * scale + 2
    margin = 48
    rows = (len(glyphs) + cols - 1) // cols
    img = Image.new("L", (margin + cols * cell_w + 1, rows * cell_h + 1), 200)
    draw = ImageDraw.Draw(img)
    for i, g in enumerate(glyphs):
        r, c = divmod(i, cols)
        x, y = margin + c * cell_w + 1, r * cell_h + 1
        img.paste(Image.fromarray(to_gray(g)).resize((w * scale, h * scale), Image.NEAREST), (x, y))
        if c == 0:
            draw.text((2, y + cell_h // 2 - 6), str(labels[i]), fill=0)
    return img


def get_full(data, i):
    o = FULL_OFS + i * GLYPH_BYTES
    return decode_4bpp(data[o:o + GLYPH_BYTES], FULL_W, FULL_H)
