# -*- coding: utf-8 -*-
"""한국어 문자열 -> 게임 텍스트 바이트.

한글은 work/font_ko/hangul.tbl 의 SJIS 한자 슬롯 코드로, 그 밖의 글자는
원래 Shift-JIS 코드로 인코딩한다. 한자·가나는 쓸 수 없다(그 자리가 한글이라서).
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TBL = os.path.join(HERE, "..", "font_ko", "hangul.tbl")

_map = None


def table():
    global _map
    if _map is None:
        _map = {}
        for line in open(TBL, encoding="utf-8"):
            line = line.rstrip("\n")
            if not line or "=" not in line:
                continue
            code, ch = line.split("=", 1)
            _map[ch] = int(code, 16)
    return _map


def is_hangul(ch):
    return "\uac00" <= ch <= "\ud7a3"


# 게임 글꼴에 남아 있는(=한글로 덮이지 않은) 전각 기호만 허용한다
BANNED_RANGES = (("\u3040", "\u30ff"), ("\u4e00", "\u9fff"))


ALLOWED = "・"          # 가운뎃점은 한자 슬롯이 아니라 그대로 쓸 수 있다


def check_char(ch):
    if is_hangul(ch) or ch in ALLOWED:
        return None
    for a, b in BANNED_RANGES:
        if a <= ch <= b:
            return "가나·한자는 쓸 수 없습니다: %r" % ch
    return None


def encode(s):
    m = table()
    out = bytearray()
    for ch in s:
        if ch in m:
            out += bytes([m[ch] >> 8, m[ch] & 0xFF])
            continue
        err = check_char(ch)
        if err:
            raise ValueError(err)
        try:
            b = ch.encode("cp932")
        except UnicodeEncodeError:
            raise ValueError("게임 글꼴에 없는 글자: %r" % ch)
        out += b
    return bytes(out)


def width(s):
    """화면 폭(반각 단위). 한글·전각 2, 반각 1."""
    w = 0
    for ch in s:
        if is_hangul(ch):
            w += 2
        else:
            try:
                w += 2 if len(ch.encode("cp932")) == 2 else 1
            except UnicodeEncodeError:
                w += 2
    return w
