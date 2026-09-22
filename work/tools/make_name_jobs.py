# -*- coding: utf-8 -*-
"""무장·도시 이름과 남은 실행파일 문자열을 번역 작업 파일로 나눈다.

  work/trans/jobs/nNNN.tsv  무장 이름 (no / 姓 / 읽기 / 名 / 읽기 / 字)
  work/trans/jobs/cNNN.tsv  도시 이름
  work/trans/jobs/xNNN.tsv  남은 실행파일 문자열
"""
import csv
import glob
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TR = os.path.join(HERE, "..", "trans")
JOBS = os.path.join(TR, "jobs")
PER_N, PER_X = 90, 200


def rows(path):
    return list(csv.DictReader(open(path, encoding="utf-8"), delimiter="\t",
                               quoting=csv.QUOTE_NONE))


def main():
    os.makedirs(JOBS, exist_ok=True)
    for pre in ("n", "c", "x"):
        for old in glob.glob(os.path.join(JOBS, pre + "[0-9][0-9][0-9].tsv")):
            os.remove(old)

    off = rows(os.path.join(TR, "names_officer.tsv"))
    n = 0
    for i in range(0, len(off), PER_N):
        n += 1
        with open(os.path.join(JOBS, "n%03d.tsv" % n), "w", encoding="utf-8", newline="\n") as f:
            f.write("no\tsei\tsei_yomi\tmei\tmei_yomi\tazana\tko_sei\tko_mei\tko_azana\n")
            for r in off[i:i + PER_N]:
                f.write("%s\t%s\t%s\t%s\t%s\t%s\t\t\t\n" % (
                    r["no"], r["sei"], r["sei_yomi"], r["mei"], r["mei_yomi"], r["azana"]))
    print("무장 %d명 -> 작업 파일 %d개" % (len(off), n))

    cs = rows(os.path.join(TR, "names_city.tsv"))
    with open(os.path.join(JOBS, "c001.tsv"), "w", encoding="utf-8", newline="\n") as f:
        f.write("no\tjp\tyomi\tko\n")
        for r in cs:
            f.write("%s\t%s\t%s\t\n" % (r["no"], r["jp"], r["yomi"]))
    print("도시 %d개 -> c001.tsv" % len(cs))

    xs = [r for r in rows(os.path.join(TR, "elf_left.tsv")) if r["ref"] == "1"]
    m = 0
    for i in range(0, len(xs), PER_X):
        m += 1
        with open(os.path.join(JOBS, "x%03d.tsv" % m), "w", encoding="utf-8", newline="\n") as f:
            f.write("offset\tcap\tjp\tko\n")
            for r in xs[i:i + PER_X]:
                f.write("%s\t%s\t%s\t\n" % (r["offset"], r["cap"], r["jp"]))
    print("실행파일 잔여 문자열 %d개 -> 작업 파일 %d개" % (len(xs), m))


if __name__ == "__main__":
    main()
