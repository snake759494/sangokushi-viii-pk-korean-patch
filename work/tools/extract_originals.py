# -*- coding: utf-8 -*-
"""원본 BIN 에서 실행파일·SAN8.BIN 을 꺼내고, 실행파일의 파일 테이블로 SAN8.BIN 내부 파일을 추출한다.

사용: python work/tools/extract_originals.py ["Sangokushi VIII with Power-Up Kit (Japan).bin"]
  - work/iso/SLPM_623.19, work/iso/SAN8.BIN 이 없으면 BIN(MODE2/2352)의 ISO9660 루트 목록에서 꺼낸다
  - 테이블 엔트리(32바이트): name_ptr, 0, start_lba, 0, end_lba, 0, sectors, 0
"""
import os, struct, sys, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
ISO_DIR = os.path.join(HERE, "..", "iso")
OUT_DIR = os.path.join(HERE, "..", "san8")

ELF_NAME = "SLPM_623.19"
ELF_TABLE = 0x4EB2A0
SAN8_LBA = 24
SECTOR = 2048

def v2o(v): return v - 0x100000 + 0x80
def o2v(o): return o - 0x80 + 0x100000

def read_table(elf):
    out = []
    i = 0
    while True:
        namep, z1, s, z2, e, z3, n, z4 = struct.unpack_from("<8I", elf, ELF_TABLE + i * 32)
        if not (0x600000 <= namep < 0x610000) or z1 or z2 or z3 or z4:
            break
        o = v2o(namep)
        name = elf[o:elf.index(b"\0", o)].decode("ascii")
        out.append((name, s, e, n))
        i += 1
    return out

def read_sector(f, lba):
    f.seek(lba * 2352 + 24)
    return f.read(SECTOR)


def extract_from_bin(bin_path, names=(ELF_NAME, "SAN8.BIN")):
    """ISO9660 기본 볼륨 기술자(16섹터)의 루트 디렉터리에서 파일을 꺼낸다."""
    os.makedirs(ISO_DIR, exist_ok=True)
    with open(bin_path, "rb") as f:
        pvd = read_sector(f, 16)
        assert pvd[1:6] == b"CD001", "ISO9660 이 아닙니다"
        root = pvd[156:156 + 34]
        rlba, rsize = struct.unpack_from("<I", root, 2)[0], struct.unpack_from("<I", root, 10)[0]
        data = b"".join(read_sector(f, rlba + k) for k in range((rsize + SECTOR - 1) // SECTOR))
        found = {}
        o = 0
        while o < len(data):
            ln = data[o]
            if ln == 0:
                o = (o // SECTOR + 1) * SECTOR
                continue
            lba, size = struct.unpack_from("<I", data, o + 2)[0], struct.unpack_from("<I", data, o + 10)[0]
            nl = data[o + 32]
            nm = data[o + 33:o + 33 + nl].decode("ascii", "replace").split(";")[0]
            if nm in names:
                found[nm] = (lba, size)
            o += ln
        for nm in names:
            lba, size = found[nm]
            with open(os.path.join(ISO_DIR, nm), "wb") as g:
                left = size
                for k in range((size + SECTOR - 1) // SECTOR):
                    b = read_sector(f, lba + k)
                    g.write(b[:min(SECTOR, left)])
                    left -= SECTOR
            print("%s: LBA %d, %d B -> work/iso/" % (nm, lba, size))


def main():
    if not os.path.exists(os.path.join(ISO_DIR, ELF_NAME)) or not os.path.exists(os.path.join(ISO_DIR, "SAN8.BIN")):
        src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "Sangokushi VIII with Power-Up Kit (Japan).bin")
        extract_from_bin(src)
    elf = open(os.path.join(ISO_DIR, ELF_NAME), "rb").read()
    pk = open(os.path.join(ISO_DIR, "SAN8.BIN"), "rb").read()
    os.makedirs(OUT_DIR, exist_ok=True)
    pk_secs = len(pk) // SECTOR
    for name, s, e, n in read_table(elf):
        inpk = SAN8_LBA <= s and s + n <= SAN8_LBA + pk_secs
        fn = name.lstrip("\\").split(";")[0]
        tag = "[SAN8 +0x%X]" % ((s - SAN8_LBA) * SECTOR) if inpk else ""
        print("%-16s lba=%6d..%-6d secs=%5d  %9d B %s" % (fn, s, e, n, n * SECTOR, tag))
        if inpk:
            rel = (s - SAN8_LBA) * SECTOR
            open(os.path.join(OUT_DIR, fn), "wb").write(pk[rel:rel + n * SECTOR])

if __name__ == "__main__":
    sys.exit(main())
