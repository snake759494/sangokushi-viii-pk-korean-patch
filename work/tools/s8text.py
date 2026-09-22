# -*- coding: utf-8 -*-
"""M_MSG.S8 컨테이너 파서 + 스크립트 토큰 분석기.

컨테이너 구조 (삼국지8PK, SLPM-62319)
  0x00  'KOEI' + 0
  0x08  u32  바깥 오프셋표의 끝(0xFFFFFFFF 위치)
  0x10  u32
  0x18  u32[]  그룹 오프셋표 (그룹 데이터 base 0x4F4 기준), 0xFFFFFFFF 로 끝
  0x4F4 부터  그룹 데이터

그룹 구조
  +0x00 u32  머리 크기 hs (= 4 + 4*항목수)
  +0x04 u32[항목수]  항목 오프셋 (그룹시작+hs 기준)
  +hs   항목 데이터

항목(스크립트) 토큰
  ('txt', b)   표시 텍스트 (Shift-JIS)
  ('code', b)  0x24 '$' + u16 코드  (+ 일부 코드는 u32 인자)
  ('nl',  b)   0x40 0x52 '@R'  줄/페이지 구분
  ('nul', b)   0x00  문자열 끝
  ('raw', b)   그 밖의 바이트
"""
import struct

MAGIC = b"KOEI"
OUTER_TBL = 0x18
DATA_BASE = 0x4F4

DOLLAR = 0x24
AT = 0x40


def is_lead(b):
    return 0x81 <= b <= 0x9F or 0xE0 <= b <= 0xFC


def parse_container(data):
    """-> Container"""
    assert data[:4] == MAGIC, "KOEI 매직 없음"
    outer = []
    i = OUTER_TBL
    while True:
        v = struct.unpack_from("<I", data, i)[0]
        if v == 0xFFFFFFFF:
            break
        outer.append(v)
        i += 4
    head = data[:DATA_BASE]
    bounds = outer + [len(data) - DATA_BASE]
    groups, raws = [], []
    prefixes = {}
    for g in range(len(outer)):
        o = DATA_BASE + outer[g]
        gsize = bounds[g + 1] - bounds[g]
        raws.append(data[o:o + gsize])
        hs = struct.unpack_from("<I", data, o)[0]
        if hs < 4 or hs % 4 or hs > gsize:
            groups.append(None)        # 스크립트가 아닌 꼬리 블록: 원본 그대로 둔다
            continue
        k = hs // 4 - 1
        offs = list(struct.unpack_from("<%dI" % k, data, o + 4)) if k else []
        db = o + hs
        dsz = gsize - hs
        ents = []
        for j in range(k):
            st = db + offs[j]
            en = db + (offs[j + 1] if j + 1 < k else dsz)
            ents.append(data[st:en])
        groups.append(ents)
        prefixes[g] = data[db:db + offs[0]] if k else b""
    return Container(head, groups, raws, len(data), prefixes)


class Container(object):
    def __init__(self, head, groups, raws, orig_size, prefixes=None):
        self.head = head
        self.groups = groups          # [ [entry bytes...] | None ]
        self.raws = raws              # 원본 그룹 바이트 (변경 없는 그룹 통과용)
        self.orig_size = orig_size
        self.prefixes = prefixes or {}

    def group_bytes(self, g):
        ents = self.groups[g]
        if ents is None:
            return self.raws[g]
        k = len(ents)
        hs = 4 + 4 * k
        pre = self.prefixes.get(g, b"")
        offs, cur = [], len(pre)
        for e in ents:
            offs.append(cur)
            cur += len(e)
        return (struct.pack("<I", hs)
                + b"".join(struct.pack("<I", x) for x in offs)
                + pre + b"".join(ents))

    def build(self, align=1):
        blobs = []
        for g in range(len(self.groups)):
            b = self.group_bytes(g)
            if len(b) % align:
                b += b"\0" * (align - len(b) % align)
            blobs.append(b)
        outer, cur = [], 0
        for b in blobs:
            outer.append(cur)
            cur += len(b)
        pre = bytearray(self.head)
        struct.pack_into("<I", pre, 0x08, OUTER_TBL + 4 * len(outer))
        for i, v in enumerate(outer):
            struct.pack_into("<I", pre, OUTER_TBL + 4 * i, v)
        struct.pack_into("<I", pre, OUTER_TBL + 4 * len(outer), 0xFFFFFFFF)
        return bytes(pre) + b"".join(blobs)


# --- 스크립트 토큰 -------------------------------------------------------

def lex(b, argmap):
    """항목 바이트열 -> 토큰 목록.

    argmap: {코드값: 인자 바이트 수} (없으면 0). set 을 주면 값 4 로 본다.
    """
    if isinstance(argmap, (set, frozenset)):
        argmap = {k: 4 for k in argmap}
    toks = []
    i, n = 0, len(b)
    start = None

    def flush(end):
        nonlocal start
        if start is not None and end > start:
            toks.append(("txt", b[start:end]))
        start = None

    while i < n:
        c = b[i]
        if c == DOLLAR and i + 3 <= n:
            flush(i)
            cid = struct.unpack_from("<H", b, i + 1)[0]
            ln = 3 + argmap.get(cid, 0)
            if i + ln > n:
                ln = 3
            toks.append(("code", b[i:i + ln]))
            i += ln
        elif c == AT and i + 1 < n and b[i + 1] == 0x52:
            flush(i)
            toks.append(("nl", b[i:i + 2]))
            i += 2
        elif c == 0x00:
            flush(i)
            toks.append(("nul", b[i:i + 1]))
            i += 1
        elif is_lead(c) and i + 1 < n:
            if start is None:
                start = i
            i += 2
        elif 0x20 <= c <= 0x7E or 0xA1 <= c <= 0xDF or c == 0x0A:
            if start is None:
                start = i
            i += 1
        else:
            flush(i)
            toks.append(("raw", b[i:i + 1]))
            i += 1
    flush(n)
    return toks


def unlex(toks):
    return b"".join(t[1] for t in toks)


def code_id(tok):
    return struct.unpack_from("<H", tok[1], 1)[0]
