# -*- coding: utf-8 -*-
"""원본 BIN(MODE2/2352) 을 복사한 뒤 work/patched/ 의 파일을 제자리에 써 넣는다.

섹터마다 사용자 데이터 2048 B 를 바꾸고 EDC/ECC 를 다시 계산한다.
M_MSG.S8 은 커지면 빈 영역(LBA 46030~)으로 옮기고, 그 위치는
work/patched/SLPM_623.19 의 파일 테이블에 이미 반영돼 있다.
"""
import os
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cdecc

ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
SRC_BIN = os.path.join(ROOT, "Sangokushi VIII with Power-Up Kit (Japan).bin")
PATCHED = os.path.join(ROOT, "work", "patched")
ELF_TABLE = 0x4EB2A0
RAW, DATA_OFF, DATA_LEN = 2352, 24, 2048

# ISO9660 상의 고정 위치 파일
FIXED = {"SLPM_623.19": 43388}


def table_entries(elf):
    out = {}
    i = 0
    while True:
        namep, z1, s, z2, e, z3, n, z4 = struct.unpack_from("<8I", elf, ELF_TABLE + i * 32)
        if not (0x600000 <= namep < 0x610000) or z1 or z2 or z3 or z4:
            break
        o = namep - 0x100000 + 0x80
        nm = elf[o:elf.index(b"\0", o)].decode("ascii").lstrip("\\").split(";")[0]
        out[nm] = (s, n)
        i += 1
    return out


def write_file(f, lba, data, log):
    n = (len(data) + DATA_LEN - 1) // DATA_LEN
    for k in range(n):
        chunk = data[k * DATA_LEN:(k + 1) * DATA_LEN]
        if len(chunk) < DATA_LEN:
            chunk += b"\0" * (DATA_LEN - len(chunk))
        off = (lba + k) * RAW
        f.seek(off)
        sec = bytearray(f.read(RAW))
        if len(sec) < RAW:
            raise SystemExit("디스크 밖 섹터 LBA %d" % (lba + k))
        sec[DATA_OFF:DATA_OFF + DATA_LEN] = chunk
        cdecc.fix_sector(sec)
        f.seek(off)
        f.write(bytes(sec))
    log.append("  LBA %6d .. %6d (%5d 섹터) %d B" % (lba, lba + n - 1, n, len(data)))


def main(out_path):
    elf_new = os.path.join(PATCHED, "SLPM_623.19")
    elf = open(elf_new, "rb").read()
    ents = table_entries(elf)

    if os.path.abspath(out_path) == os.path.abspath(SRC_BIN):
        raise SystemExit("원본을 덮어쓸 수 없습니다")
    print("원본 복사 중...")
    shutil.copyfile(SRC_BIN, out_path)

    log = []
    with open(out_path, "r+b") as f:
        for name in sorted(os.listdir(PATCHED)):
            path = os.path.join(PATCHED, name)
            if not os.path.isfile(path):
                continue
            data = open(path, "rb").read()
            if name in FIXED:
                lba = FIXED[name]
            elif name in ents:
                lba = ents[name][0]
            else:
                print("  건너뜀(위치 모름):", name)
                continue
            print("쓰는 중:", name)
            log.append(name)
            write_file(f, lba, data, log)
    print("\n".join(log))
    print("완성:", out_path, os.path.getsize(out_path), "B")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else
         os.path.join(ROOT, "Sangokushi VIII with Power-Up Kit (Korean).bin"))
