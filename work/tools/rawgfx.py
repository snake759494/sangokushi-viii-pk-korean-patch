# -*- coding: utf-8 -*-
"""무압축 G_*.S8: [팔레트 1KB x n][8비트 픽셀...] 을 폭 w 로 그려 본다."""
import sys, os, numpy as np
from PIL import Image
W = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
def unsw(p):
    i = np.arange(256); return p[(i & 0xE7) | ((i & 0x08) << 1) | ((i & 0x10) >> 1)]
def npal(d):
    n = 0
    while (n + 1) * 1024 <= len(d):
        a = np.frombuffer(d[n*1024:(n+1)*1024], np.uint8)[3::4]
        if not np.isin(a, (0, 0x80)).all(): break
        n += 1
    return n
def pal(d, k): return unsw(np.frombuffer(d[k*1024:(k+1)*1024], np.uint8).reshape(256, 4)[:, :3])
if __name__ == "__main__":
    f, w = sys.argv[1], int(sys.argv[2])
    d = open(os.path.join(W, "san8", f), "rb").read()
    n = npal(d); px = np.frombuffer(d[n*1024:], np.uint8); h = len(px) // w
    print(f, "palettes", n, "pixels", len(px), "h", h)
    img = pal(d, 0)[px[:w*h].reshape(h, w)]
    Image.fromarray(img).save(os.path.join(W, "gfx", "prev", "%s_%d.png" % (f, w)))
