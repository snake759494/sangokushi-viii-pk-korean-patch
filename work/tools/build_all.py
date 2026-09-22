# -*- coding: utf-8 -*-
"""원본 BIN 에서 배포용 한글 BIN 까지 한 번에 만든다 (docs/BUILD.md 의 순서).

사용: python work/tools/build_all.py ["원본.bin"] ["결과.bin"]
준비: 저장소 루트에 원본 BIN 과 글꼴(SeoulHangangB.ttf, SeoulHangangEB.ttf, NanumSquareNeo-cBd.ttf)
"""
import os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "Sangokushi VIII with Power-Up Kit (Japan).bin")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "Sangokushi VIII with Power-Up Kit (Korean).bin")
STEPS = [
    ("extract_originals.py", [SRC]),   # 실행파일·SAN8.BIN 추출, SAN8.BIN 안 41개 파일
    ("font_build_ko.py", []),          # F_FONT.S8 한글 2,350자
    ("build_names.py", []),            # D_SCE.S8 무장·도시·주·이름 칸
    ("gfx_main.py", []),               # G_MAIN.S8
    ("gfx_raw.py", []),                # G_GUNGI / G_WARGRP / G_IKBG
    ("gfx_wargrp4.py", []),            # G_WARGRP 4비트 (gfx_raw 뒤)
    ("gfx_sys4.py", []),               # G_SYSTEM 4비트
    ("gfx_legend.py", []),             # G_SYSTEM 범례 (gfx_sys4 뒤)
    ("gfx_emtmp.py", []),              # G_EMTMP 주 이름
    ("build_text.py", []),             # M_MSG.S8 · SLPM_623.19
    ("build_bin.py", [OUT]),           # BIN 에 써 넣고 EDC/ECC
]


def main():
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    for script, args in STEPS:
        print("==", script, flush=True)
        r = subprocess.run([sys.executable, os.path.join(HERE, script)] + args, cwd=ROOT, env=env)
        if r.returncode != 0:
            raise SystemExit("%s 실패 (exit %d)" % (script, r.returncode))
    print("완료:", OUT)


if __name__ == "__main__":
    main()
