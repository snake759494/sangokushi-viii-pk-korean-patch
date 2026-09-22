# -*- coding: utf-8 -*-
"""D_SCE.S8 의 무장·도시 이름을 읽고 쓴다.

무장 레코드 (0x4F 바이트). 문자열 칸은 자리가 고정돼 있고 NUL 로 끝난다.

  +0x00  u16  무장 번호 (0,1,2,… 로 이어진다)
  +0x02   5B  姓        (전각 2자 + NUL)
  +0x07  11B  姓 읽기   (반각 가나)
  +0x12   5B  名        (전각 2자 + NUL)
  +0x17  11B  名 읽기
  +0x22   5B  字        (전각 2자 + NUL)
  +0x27  부터 능력치 등 이진 데이터 (건드리지 않는다)

도시 레코드 (0x11 바이트, 파일 앞 0x24 부터): 이름 NUL 읽기 NUL 나머지 공백
"""
import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "san8", "D_SCE.S8")

REC = 0x4F
# (이름, 오프셋, 칸 크기)
FIELDS = (("sei", 0x02, 5), ("sei_yomi", 0x07, 11),
          ("mei", 0x12, 5), ("mei_yomi", 0x17, 11),
          ("azana", 0x22, 5))
CITY_OFF, CITY_REC = 0x24, 0x11


def is_lead(b):
    return 0x81 <= b <= 0x9F or 0xE0 <= b <= 0xFC


def _get(data, o, off, size):
    seg = data[o + off:o + off + size]
    e = seg.find(b"\x00")
    return (seg if e < 0 else seg[:e]).strip(b"\x20")


def _put(data, o, off, size, val):
    if len(val) + 1 > size:
        raise ValueError("칸 %d B 에 %d B 는 안 들어감: %r" % (size, len(val) + 1, val))
    data[o + off:o + off + size] = val + b"\x00" + b"\x20" * (size - len(val) - 1)


def find_first_record(data):
    for base in range(0, 0x8000):
        ok = True
        for k in range(8):
            p = base + k * REC
            if p + REC > len(data) or struct.unpack_from("<H", data, p)[0] != k \
                    or not is_lead(data[p + 2]):
                ok = False
                break
        if ok:
            return base
    return None


def officers(data, base=None, limit=1500):
    """[(번호, 레코드시작, {칸이름: 바이트})]"""
    if base is None:
        base = find_first_record(data)
    out, n = [], 0
    while base + (n + 1) * REC <= len(data) and n < limit:
        o = base + n * REC
        if struct.unpack_from("<H", data, o)[0] != n or not is_lead(data[o + 2]):
            break
        out.append((n, o, {k: _get(data, o, off, size) for k, off, size in FIELDS}))
        n += 1
    return base, out


def write_officer(data, o, rec):
    for k, off, size in FIELDS:
        _put(data, o, off, size, rec[k])


def cities(data, limit=200):
    """[(번호, 위치, 이름, 읽기)]"""
    out = []
    for n in range(limit):
        o = CITY_OFF + n * CITY_REC
        if o + CITY_REC > len(data) or not is_lead(data[o]):
            break
        e = data.find(b"\x00", o)
        r = e + 1
        e2 = data.find(b"\x00", r)
        if e2 < 0 or e2 >= o + CITY_REC:
            break
        out.append((n, o, data[o:e], data[r:e2]))
    return out


def write_city(data, o, name, yomi):
    body = name + b"\x00" + yomi + b"\x00"
    if len(body) > CITY_REC:
        raise ValueError("도시 칸 %d B 초과: %d B" % (CITY_REC, len(body)))
    data[o:o + CITY_REC] = body + b"\x20" * (CITY_REC - len(body))
