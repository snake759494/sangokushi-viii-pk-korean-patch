# -*- coding: utf-8 -*-
"""Mode 2 Form 1 섹터의 EDC / ECC(P,Q) 계산.

섹터 2352 B 배치
  0x000 sync 12  0x00C 헤더 4  0x010 서브헤더 8  0x018 사용자 데이터 2048
  0x818 EDC 4    0x81C ECC P 172  0x8C8 ECC Q 104
EDC 는 0x010~0x817 (2056 B) 에 대해, ECC 는 헤더를 0 으로 둔 0x00C~0x81B 에 대해 구한다.
"""
import numpy as np

_f = np.zeros(256, dtype=np.uint8)
_b = np.zeros(256, dtype=np.uint8)
_edc = np.zeros(256, dtype=np.uint32)
for _i in range(256):
    _j = ((_i << 1) ^ (0x11D if _i & 0x80 else 0)) & 0xFF
    _f[_i] = _j
    _b[_i ^ _j] = _i
    _e = _i
    for _k in range(8):
        _e = (_e >> 1) ^ (0xD8018001 if _e & 1 else 0)
    _edc[_i] = _e


_EDC = [int(x) for x in _edc]


def edc(buf):
    v = 0
    for b in bytes(buf):
        v = (v >> 8) ^ _EDC[(v ^ b) & 0xFF]
    return v & 0xFFFFFFFF


def _index_table(major_count, minor_count, major_mult, minor_inc):
    size = major_count * minor_count
    idx = np.empty((major_count, minor_count), dtype=np.int32)
    for major in range(major_count):
        i = (major >> 1) * major_mult + (major & 1)
        for minor in range(minor_count):
            idx[major, minor] = i
            i += minor_inc
            if i >= size:
                i -= size
    return idx


_P_IDX = _index_table(86, 24, 2, 86)
_Q_IDX = _index_table(52, 43, 86, 88)


def _ecc(src, idx):
    """src: uint8 배열(2064 B 중 앞부분). idx: (major, minor) 인덱스표."""
    vals = src[idx]                       # (major, minor)
    major_count, minor_count = idx.shape
    a = np.zeros(major_count, dtype=np.uint8)
    b = np.zeros(major_count, dtype=np.uint8)
    for m in range(minor_count):
        t = vals[:, m]
        a ^= t
        b ^= t
        a = _f[a]
    a = _b[_f[a] ^ b]
    return np.concatenate([a, (a ^ b).astype(np.uint8)])


def fix_sector(sec):
    """sec: bytearray(2352) — EDC/ECC 를 계산해 제자리에 쓴다."""
    a = np.frombuffer(bytes(sec), dtype=np.uint8).copy()
    v = edc(a[0x10:0x818])
    a[0x818:0x81C] = [v & 0xFF, (v >> 8) & 0xFF, (v >> 16) & 0xFF, (v >> 24) & 0xFF]
    # ECC 계산 구간: 0x00C 부터. P 는 앞 2064 B, Q 는 P 결과까지 포함한 2236 B.
    work = a[0x0C:0x0C + 2236].copy()
    work[0:4] = 0                         # Mode 2 는 헤더를 0 으로 두고 계산
    p = _ecc(work, _P_IDX)
    a[0x81C:0x8C8] = p
    work[0x81C - 0x0C:0x8C8 - 0x0C] = p
    a[0x8C8:0x930] = _ecc(work, _Q_IDX)
    sec[:] = a.tobytes()
    return sec
