"""BIN(MODE2/2352) <-> ISO(2048) 변환. 8PK 디스크는 Mode 2 Form 1 전 섹터."""
import sys, os

SECT_RAW = 2352
DATA_OFF = 24
DATA_LEN = 2048

def bin2iso(src, dst):
    n = os.path.getsize(src) // SECT_RAW
    with open(src, 'rb') as f, open(dst, 'wb') as g:
        for i in range(n):
            f.seek(i * SECT_RAW + DATA_OFF)
            g.write(f.read(DATA_LEN))
    return n

if __name__ == '__main__':
    n = bin2iso(sys.argv[1], sys.argv[2])
    print('sectors', n, '->', os.path.getsize(sys.argv[2]))
