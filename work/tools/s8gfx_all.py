import os, sys, struct
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "title"))
from gamedec import game_decode
W = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
def scan_all(d):
    res = []; o = 0; n = len(d)
    while o + 16 <= n:
        t, u, co, lo = struct.unpack_from("<4I", d, o)
        if t in (0,1,2,3) and 0x100 <= u <= 0x400000 and 16 <= co <= lo < n - o and co % 1 == 0 and lo - co < u:
            try:
                out, info = game_decode(d, o, maxout=u + 64)
                if not info.get("overflow") and info["n"] == u:
                    end = o + max(info["lits_end"], info["end_code_at"] + 2)
                    res.append((o, t, u, end, out)); o = (end + 15) & ~15; continue
            except Exception:
                pass
        o += 16
    return res
if __name__ == "__main__":
    for f in sys.argv[1:]:
        d = open(os.path.join(W, "san8", f), "rb").read()
        r = scan_all(d)
        print(f, len(r), "blocks; covered", sum(e - o for o, t, u, e, _ in r), "/", len(d))
        for i, (o, t, u, e, out) in enumerate(r):
            open(os.path.join(W, "gfx", "dec", "%s_%03d.bin" % (f, i)), "wb").write(out)
            if i < 400: print("  %3d %7x t%d u%6x" % (i, o, t, u))
