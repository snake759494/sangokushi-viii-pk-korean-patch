# -*- coding: utf-8 -*-
"""SLPM_623.19 안에서 '참조되는 주소' 집합을 구한다.

1) 데이터 속 32비트 포인터 (적재 구간 범위의 값)
2) 코드의 lui + addiu/ori/lw/lb/... 짝 (같은 레지스터, 24명령 이내)
"""
import struct
import numpy as np

BASE_V, BASE_F = 0x100000, 0x80
SEG_SIZE = 0x528900


def v2o(v): return v - BASE_V + BASE_F
def o2v(o): return o - BASE_F + BASE_V


def refs(d):
    n = (len(d) - BASE_F) // 4
    w = np.frombuffer(d, dtype="<u4", count=n, offset=BASE_F)
    lo_v, hi_v = BASE_V, BASE_V + SEG_SIZE
    out = set(int(x) for x in w[(w >= lo_v) & (w < hi_v)])

    op = w >> 26
    lui_idx = np.nonzero(op == 0x0F)[0]
    rt_all = (w >> 16) & 31
    rs_all = (w >> 21) & 31
    imm_all = w & 0xFFFF
    ADD = (0x09, 0x08, 0x19, 0x18)
    LOAD = (0x20, 0x21, 0x23, 0x24, 0x25, 0x28, 0x29, 0x2B, 0x37, 0x3F, 0x1E, 0x1F)
    for i in lui_idx:
        rt = int(rt_all[i])
        hi = int(imm_all[i]) << 16
        for j in range(i + 1, min(i + 25, n)):
            o2 = int(op[j]); rs = int(rs_all[j]); rt2 = int(rt_all[j]); imm = int(imm_all[j])
            if rs == rt:
                if o2 in ADD or o2 in LOAD:
                    s = imm - 0x10000 if imm & 0x8000 else imm
                    out.add((hi + s) & 0xFFFFFFFF)
                elif o2 == 0x0D:
                    out.add(hi | imm)
            if rt2 == rt and o2 not in (0x2B, 0x29, 0x28, 0x3F, 0x1F, 0x04, 0x05):
                break
    return out
