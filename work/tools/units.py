# -*- coding: utf-8 -*-
"""M_MSG.S8 항목 <-> 태그 문자열 변환 (번역 단위).

태그
  ⏎          @R  (줄/페이지 구분)
  ‖          NUL (문자열 끝)
  {XXXX}     $코드 (16진 4자리)
  {XXXX:n}   $코드 + u32 인자
  {r:hh}     그 밖의 제어 바이트
텍스트는 CP932 로 디코드해 그대로 둔다.
"""
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import s8text

NL, NUL = "\u23CE", "\u2016"
TAG = re.compile(r"\{([0-9A-Fa-f]{4})(?::([0-9,]+))?\}|\{r:([0-9A-Fa-f]{2})\}")


def load_args(path=None):
    """{코드값: 인자 바이트 수}"""
    path = path or os.path.join(HERE, "..", "trans", "code_args.txt")
    m = {}
    for line in open(path, encoding="utf-8"):
        if line.startswith("#") or not line.strip():
            continue
        cid, nb = line.split("\t")[:2]
        if int(nb):
            m[int(cid)] = int(nb)
    return m


def has_jp(b):
    return any(s8text.is_lead(x) or 0xA1 <= x <= 0xDF for x in b)


def to_text(entry, ops):
    out = []
    for kind, v in s8text.lex(entry, ops):
        if kind == "txt":
            out.append(v.decode("cp932"))
        elif kind == "nl":
            out.append(NL)
        elif kind == "nul":
            out.append(NUL)
        elif kind == "code":
            cid = struct.unpack_from("<H", v, 1)[0]
            na = (len(v) - 3) // 4
            if na:
                vals = struct.unpack_from("<%dI" % na, v, 3)
                out.append("{%04X:%s}" % (cid, ",".join(str(x) for x in vals)))
            else:
                out.append("{%04X}" % cid)
        else:
            out.append("{r:%02X}" % v[0])
    return "".join(out)


def from_text(s, enc):
    """태그 문자열 -> 바이트열. enc(str)->bytes 로 텍스트를 인코딩한다."""
    out = bytearray()
    i = 0
    buf = []

    def flush():
        if buf:
            out.extend(enc("".join(buf)))
            del buf[:]

    while i < len(s):
        ch = s[i]
        if ch == NL:
            flush(); out += b"\x40\x52"; i += 1
        elif ch == NUL:
            flush(); out += b"\x00"; i += 1
        elif ch == "{":
            m = TAG.match(s, i)
            if not m:
                raise ValueError("태그 형식 오류: ...%s" % s[i:i + 12])
            flush()
            if m.group(3) is not None:
                out.append(int(m.group(3), 16))
            else:
                cid = int(m.group(1), 16)
                out += b"\x24" + struct.pack("<H", cid)
                if m.group(2) is not None:
                    for x in m.group(2).split(","):
                        out += struct.pack("<I", int(x))
            i = m.end()
        else:
            buf.append(ch); i += 1
    flush()
    return bytes(out)


def jp_enc(s):
    return s.encode("cp932")


def iter_entries(container, ops):
    for g, ents in enumerate(container.groups):
        if not ents:
            continue
        for i, e in enumerate(ents):
            yield g, i, e
