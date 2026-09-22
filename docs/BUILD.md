# 재빌드 절차

저장소의 소스와 번역 데이터만으로 배포용 BIN 을 다시 만드는 순서입니다.
게임 원본과 글꼴은 사용자가 준비해야 하며, 명령은 저장소 루트에서 실행합니다.

## 준비물

| 항목 | 비고 |
| --- | --- |
| Python 3.11 이상 | `pip install -r requirements.txt` (numpy, scipy, Pillow) |
| 원본 BIN | README 의 해시와 같은 `Sangokushi VIII with Power-Up Kit (Japan).bin` 을 루트에 |
| 서울한강체 `SeoulHangangB.ttf`, `SeoulHangangEB.ttf` | 루트에. 게임 글꼴(B)과 그림 글자(EB). 서울특별시 배포 |
| 나눔스퀘어 네오 `NanumSquareNeo-cBd.ttf` | 루트에. 전투 부대 상태 표시(도발·위임·지시)의 작은 글자 |
| xdelta3 | 배포 패치 만들기·적용 |

## 한 번에 빌드

```powershell
python work/tools/build_all.py
```

아래 1~5 단계를 순서대로 실행해 루트에 `Sangokushi VIII with Power-Up Kit (Korean).bin` 을 만듭니다.
결과는 배포판과 바이트 단위로 같아야 합니다(`release_manifest.json` 의 `output_bin`).

## 1. 원본 추출

```powershell
python work/tools/extract_originals.py "Sangokushi VIII with Power-Up Kit (Japan).bin"
```

BIN(MODE2/2352)의 ISO9660 루트 목록에서 `SLPM_623.19`(실행파일)과 `SAN8.BIN` 을 `work/iso/` 로 꺼내고,
실행파일의 파일 테이블(0x4EB2A0)로 `SAN8.BIN` 안 41개 파일을 `work/san8/` 로 풉니다.

## 2. 한글 글꼴

```powershell
python work/tools/font_build_ko.py
```

`work/san8/F_FONT.S8` 의 한자 슬롯(SJIS 0x889F~0x94FC, 인덱스 340~2689)에 KS X 1001
한글 2,350자를 서울한강체 B 22px(기준선 21)로 그려 `work/patched/F_FONT.S8` 과
`work/font_ko/hangul.tbl` 을 만듭니다. 크기가 원본과 같아 제자리에 들어갑니다.

## 3. 이름 데이터와 그림 글자

```powershell
python work/tools/build_names.py     # D_SCE.S8: 무장·도시·주·아이템 이름 (가나 읽기 칸 비움)
python work/tools/gfx_main.py        # G_MAIN.S8: 안내판·신분 배지·표식·업무 명령/결과 판
python work/tools/gfx_raw.py         # G_GUNGI / G_WARGRP / G_IKBG: 전투·일기토 정보창
python work/tools/gfx_wargrp4.py     # G_WARGRP 4비트: 부대 상태 표시·총/참 (gfx_raw 뒤)
python work/tools/gfx_sys4.py        # G_SYSTEM 4비트 아이콘·전투 안내판·부대 종류 표시
python work/tools/gfx_legend.py      # G_SYSTEM 지도 범례 (gfx_sys4 뒤)
python work/tools/gfx_emtmp.py       # G_EMTMP: 전략 지도 주 이름
```

## 4. 텍스트와 실행파일

```powershell
python work/tools/build_text.py
```

`work/trans/units.tsv`(M_MSG 번역)와 `work/trans/elf_strings.tsv`(실행파일 문자열)를 적용해
`work/patched/M_MSG.S8`, `work/patched/SLPM_623.19` 를 만듭니다.

- 번역으로 길이가 바뀐 그룹은 점프·페이지 위치 인자(`$0011` `$0013` `$0015` `$0019` `$053B`)를
  새 위치로 옮깁니다. 확인: `python work/tools/check_offsets.py`.
- M_MSG 가 원래 1,103섹터보다 커지면 빈 영역(LBA 46030~)으로 옮기고 파일 테이블의
  시작 LBA·끝 LBA·섹터 수를 함께 고칩니다. 결과 요약은 `work/trans/build_report.txt`.

번역 검사는 `python work/tools/validate.py` (태그 뼈대·줄 수·글자 집합·줄 폭·`N` 뒤 조사).

## 5. BIN

```powershell
python work/tools/build_bin.py "Sangokushi VIII with Power-Up Kit (Korean).bin"
```

원본 BIN 을 복사한 뒤 `work/patched/` 의 파일을 제자리 섹터에 써 넣고, 섹터마다
Mode 2 Form 1 의 **EDC/ECC 를 다시 계산**합니다(`work/tools/cdecc.py`).
원본 섹터를 그대로 다시 계산하면 바이트가 같다는 것으로 구현을 검증했습니다.
`.cue` 는 원본 것을 이름만 바꿔 쓰면 됩니다.

## 6. 배포 패치

```powershell
.\xdelta3.exe -e -9 -S none -A -s "Sangokushi VIII with Power-Up Kit (Japan).bin" "Sangokushi VIII with Power-Up Kit (Korean).bin" Sangokushi_VIII_PK_KO_v1.0.3.xdelta
```

## 번역을 고칠 때

- 번역 규칙은 `work/trans/번역규칙.md` 입니다. `units.tsv` 를 직접 고친 뒤 `validate.py` 로 검사하고
  4·5단계를 다시 실행합니다. 줄 폭 한계는 `work/trans/unit_limits.tsv`(`unit_limits.py` 로 생성).
- 말투 매크로(그룹 0)를 바꿀 때만: `macro_table.py` → `macro_ko.py`(`work/trans/ko/macros.tsv`) →
  `apply_macros.py` 로 `units.tsv` 의 그룹 0 을 다시 채웁니다.
- 사람이 읽는 대역표 `translation/*.tsv` 는 `python work/tools/export_tables.py` 로 다시 만듭니다.
