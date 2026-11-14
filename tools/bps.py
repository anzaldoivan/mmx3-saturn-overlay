#!/usr/bin/env python3
"""Minimal BPS patch writer and applier (beat/byuu BPS1 format), standard library only.

  bps.py make  SOURCE TARGET OUT.bps [--meta TEXT]   same-size files only (sparse in-place edits)
  bps.py apply SOURCE PATCH.bps OUT                  full applier: all four actions, all three CRC32s checked

Writer emits SourceRead for equal runs and TargetRead for changed runs (gaps under 8 bytes merged).
"""
import sys, zlib

CHUNK = 1 << 20


def enc(n):
    out = bytearray()
    while True:
        x = n & 0x7F
        n >>= 7
        if n == 0:
            out.append(0x80 | x)
            return bytes(out)
        out.append(x)
        n -= 1


def dec(buf, pos):
    n, shift = 0, 1
    while True:
        x = buf[pos]
        pos += 1
        n += (x & 0x7F) * shift
        if x & 0x80:
            return n, pos
        shift <<= 7
        n += shift


def crc_file(path):
    c = 0
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(CHUNK), b''):
            c = zlib.crc32(b, c)
    return c & 0xFFFFFFFF


def diff_runs(src, tgt, merge=8):
    """[(start, end)] of differing byte ranges, gaps < merge joined."""
    runs = []
    with open(src, 'rb') as a, open(tgt, 'rb') as b:
        off = 0
        while True:
            x, y = a.read(CHUNK), b.read(CHUNK)
            if not x and not y:
                break
            if len(x) != len(y):
                sys.exit('make: files differ in size')
            if x != y:
                for i in range(len(x)):
                    if x[i] != y[i]:
                        p = off + i
                        if runs and p - runs[-1][1] < merge:
                            runs[-1][1] = p + 1
                        else:
                            runs.append([p, p + 1])
            off += len(x)
    return runs, off


def make(src, tgt, out, meta=b''):
    runs, size = diff_runs(src, tgt)
    p = bytearray(b'BPS1')
    p += enc(size) + enc(size) + enc(len(meta)) + meta
    pos = 0
    with open(tgt, 'rb') as t:
        for s, e in runs:
            if s > pos:
                p += enc(((s - pos) - 1) << 2 | 0)   # SourceRead
            t.seek(s)
            p += enc(((e - s) - 1) << 2 | 1) + t.read(e - s)  # TargetRead
            pos = e
    if size > pos:
        p += enc(((size - pos) - 1) << 2 | 0)
    p += crc_file(src).to_bytes(4, 'little') + crc_file(tgt).to_bytes(4, 'little')
    p += (zlib.crc32(p) & 0xFFFFFFFF).to_bytes(4, 'little')
    open(out, 'wb').write(p)
    print(f'make: {len(runs)} changed runs, {sum(e - s for s, e in runs)} bytes; patch {len(p)} B -> {out}')


def apply(src, patch, out):
    p = open(patch, 'rb').read()
    if p[:4] != b'BPS1':
        sys.exit('apply: not a BPS1 patch')
    if zlib.crc32(p[:-4]) & 0xFFFFFFFF != int.from_bytes(p[-4:], 'little'):
        sys.exit('apply: patch CRC mismatch')
    s = open(src, 'rb').read()
    if zlib.crc32(s) & 0xFFFFFFFF != int.from_bytes(p[-12:-8], 'little'):
        sys.exit('apply: source CRC mismatch (wrong input file)')
    pos = 4
    ssize, pos = dec(p, pos)
    tsize, pos = dec(p, pos)
    msize, pos = dec(p, pos)
    pos += msize
    if ssize != len(s):
        sys.exit('apply: source size mismatch')
    t = bytearray(tsize)
    o = srel = trel = 0
    end = len(p) - 12
    while pos < end:
        d, pos = dec(p, pos)
        cmd, n = d & 3, (d >> 2) + 1
        if cmd == 0:
            t[o:o + n] = s[o:o + n]
        elif cmd == 1:
            t[o:o + n] = p[pos:pos + n]
            pos += n
        else:
            v, pos = dec(p, pos)
            v = -(v >> 1) if v & 1 else v >> 1
            if cmd == 2:
                srel += v
                t[o:o + n] = s[srel:srel + n]
                srel += n
            else:
                trel += v
                for k in range(n):
                    t[o + k] = t[trel + k]
                trel += n
        o += n
    if o != tsize:
        sys.exit('apply: output size mismatch')
    if zlib.crc32(t) & 0xFFFFFFFF != int.from_bytes(p[-8:-4], 'little'):
        sys.exit('apply: target CRC mismatch')
    open(out, 'wb').write(t)
    print(f'apply: ok, {tsize} B -> {out}')


if __name__ == '__main__':
    a = sys.argv[1:]
    if a and a[0] in ('-h', '--help'):
        print(__doc__)
        sys.exit(0)
    if len(a) >= 4 and a[0] == 'make':
        meta = a[a.index('--meta') + 1].encode() if '--meta' in a else b''
        make(a[1], a[2], a[3], meta)
    elif len(a) == 4 and a[0] == 'apply':
        apply(a[1], a[2], a[3])
    else:
        sys.exit(__doc__)
