# -*- coding: utf-8 -*-
"""사람이 읽는 대역표를 translation/ 에 만든다 (빌드 입력은 work/trans/ 쪽).

translation/script.tsv        M_MSG.S8 번역 단위 (그룹, 항목, 일본어, 한국어)
translation/elf_strings.tsv   실행파일 문자열 (파일 오프셋, 일본어, 한국어)
translation/names_officer.tsv 무장 이름 (성·이름·자)
translation/names_place.tsv   도시 50곳·주 16곳
translation/names_data.tsv    D_SCE.S8 의 그 밖의 이름 칸 (아이템·관직·시설 등)
도시 일본어 이름은 원본 work/san8/D_SCE.S8 에서 읽는다.
"""
import csv, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import elf_strings
import build_names
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
TR = os.path.join(ROOT, "work", "trans")
OUT = os.path.join(ROOT, "translation")


def rows(name):
    return list(csv.DictReader(open(os.path.join(TR, name), encoding="utf-8"), delimiter="\t",
                               quoting=csv.QUOTE_NONE))


def write(name, head, data):
    with open(os.path.join(OUT, name), "w", encoding="utf-8", newline="\n") as f:
        f.write("\t".join(head) + "\n")
        for r in data:
            f.write("\t".join(str(x) for x in r) + "\n")
    print(name, len(data))


def sjis_name(b):
    out = ""
    i = 0
    while i < len(b):
        if b[i] >= 0xF0:
            out += "〓"; i += 2
        else:
            out += b[i:i + 2].decode("cp932", "replace"); i += 2
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    write("script.tsv", ("group", "entry", "jp", "ko"),
          [(r["group"], r["entry"], r["jp"], r["ko"]) for r in rows("units.tsv")])
    write("elf_strings.tsv", ("offset", "jp", "ko"),
          [("0x%06X" % int(r["offset"]), r["jp"], r["ko"]) for r in rows("elf_strings.tsv")])
    write("names_officer.tsv", ("no", "sei", "mei", "azana", "ko_sei", "ko_mei", "ko_azana"),
          [(r["no"], r["sei"], r["mei"], r["azana"], r["ko_sei"], r["ko_mei"], r["ko_azana"])
           for r in rows("names_officer.tsv")])
    d = open(os.path.join(ROOT, "work", "san8", "D_SCE.S8"), "rb").read()
    place = []
    for k, ko in enumerate(build_names.CITIES):
        o = build_names.CITY_BASE + 16 * k
        place.append(("도시", k, sjis_name(d[o + 4:o + 9].split(b"\0")[0]), ko))
    ds = rows("dsce_strings.tsv")
    for r in ds:
        o = int(r["offset"])
        if 0x24 <= o < 0x24 + 17 * 16 and (o - 0x24) % 17 == 0:
            place.append(("주", (o - 0x24) // 17, elf_strings.unesc(r["jp"]), r["ko"]))
    write("names_place.tsv", ("kind", "no", "jp", "ko"), place)
    write("names_data.tsv", ("offset", "jp", "ko"),
          [("0x%05X" % int(r["offset"]), r["jp"], r["ko"]) for r in ds
           if r["kind"] == "text" and not (0x24 <= int(r["offset"]) < 0x24 + 17 * 16)])


if __name__ == "__main__":
    main()
