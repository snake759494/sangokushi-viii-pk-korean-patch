# -*- coding: utf-8 -*-
"""번역 단위 검사: 태그·줄·문자열 구조, 글자 집합, 줄 폭, N 뒤 조사."""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ko_enc

TAG = re.compile(r"\{[0-9A-F]{4}(?::[0-9,]+)?\}")
NL, NUL = "\u23ce", "\u2016"
BAD_JOSA = ("을", "를", "이", "가", "은", "는", "과", "와", "로", "으로",
            "나", "야", "아", "여", "라", "란", "랑", "였")
LIMITS = None


def limits():
    global LIMITS
    if LIMITS is None:
        LIMITS = {}
        p = os.path.join(HERE, "..", "trans", "group_limits.tsv")
        for line in open(p, encoding="utf-8"):
            if line.startswith("group"):
                continue
            g, lim, _ = line.split("\t")
            LIMITS[int(g)] = int(lim)
    return LIMITS


UNIT_LIMITS = None


def unit_limits():
    """단위별 줄 폭 한계. 원문이 상자에 맞춰 나뉜 것을 기준으로 삼는다."""
    global UNIT_LIMITS
    if UNIT_LIMITS is None:
        UNIT_LIMITS = {}
        p = os.path.join(HERE, "..", "trans", "unit_limits.tsv")
        if os.path.exists(p):
            for line in open(p, encoding="utf-8"):
                if line.startswith("group"):
                    continue
                g, e, lim = line.split("\t")
                UNIT_LIMITS[(int(g), int(e))] = int(lim)
    return UNIT_LIMITS


def skeleton(s):
    """태그·⏎·‖ 의 열(텍스트를 뺀 뼈대)."""
    return tuple(m.group(0) for m in re.finditer(
        r"\{[0-9A-F]{4}(?::[0-9,]+)?\}|" + NL + "|" + NUL, s))


def width(s):
    t = 0
    for ch in s:
        if "\uac00" <= ch <= "\ud7a3":
            t += 2
        else:
            try:
                t += 2 if len(ch.encode("cp932")) == 2 else 1
            except UnicodeEncodeError:
                t += 2
    return t


def check_with_limit(jp, ko, lim):
    return _check(jp, ko, lim)


def check(group, jp, ko, entry=None):
    if entry is not None:
        lim = unit_limits().get((group, entry))
        if lim is not None:
            return _check(jp, ko, lim)
    return _check(jp, ko, limits().get(group, 40))


def _check(jp, ko, lim):
    errs = []
    if not ko.strip():
        return ["번역 없음"]
    sj, sk = skeleton(jp), skeleton(ko)
    if sj != sk:
        for a, b in zip(sj, sk):
            if a != b:
                errs.append("뼈대 다름: 원문 %s -> 번역 %s" % (a, b))
                break
        else:
            errs.append("뼈대 개수 다름: 원문 %d -> 번역 %d" % (len(sj), len(sk)))
    if jp.count(NL) != ko.count(NL):
        errs.append("줄 수(⏎) 다름: %d -> %d" % (jp.count(NL), ko.count(NL)))
    if jp.count(NUL) != ko.count(NUL):
        errs.append("‖ 개수 다름: %d -> %d" % (jp.count(NUL), ko.count(NUL)))
    plain_ko = TAG.sub("", ko).replace(NUL, "")
    for ch in plain_ko:
        if ch == "\u30fb":          # \uac00\uc6b4\ub383\uc810\uc740 \uadf8\ub300\ub85c \uc4f8 \uc218 \uc788\ub2e4
            continue
        if "\u3040" <= ch <= "\u30ff" or "\u4e00" <= ch <= "\u9fff":
            errs.append("가나·한자가 남음: %r" % ch)
            break
    try:
        ko_enc.encode(plain_ko.replace(NL, ""))
    except ValueError as e:
        errs.append(str(e))
    for line in plain_ko.split(NL):
        w = width(line)
        if w > lim:
            errs.append("줄 폭 %d > %d: %s" % (w, lim, line[:40]))
    # N 뒤 조사
    for m in re.finditer(r"N", ko):
        rest = ko[m.end():].lstrip(NUL)
        for j in sorted(BAD_JOSA, key=len, reverse=True):
            if rest.startswith(j):
                nxt = rest[len(j):len(j) + 1]
                if not ("\uac00" <= nxt <= "\ud7a3"):
                    errs.append("N 뒤에 받침 조사 '%s'" % j)
                break
    return errs


def main(path=None):
    import csv
    path = path or os.path.join(HERE, "..", "trans", "units.tsv")
    rows = list(csv.DictReader(open(path, encoding="utf-8"), delimiter="\t",
                               quoting=csv.QUOTE_NONE))
    done = bad = 0
    msgs = []
    for r in rows:
        if not r["ko"].strip():
            continue
        done += 1
        e = check(int(r["group"]), r["jp"], r["ko"], int(r["entry"]))
        if e:
            bad += 1
            msgs.append("g%s e%s: %s" % (r["group"], r["entry"], " / ".join(e[:3])))
    print("번역 %d/%d, 오류 단위 %d" % (done, len(rows), bad))
    for m in msgs[:60]:
        print("  " + m)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
