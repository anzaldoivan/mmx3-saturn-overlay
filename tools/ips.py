#!/usr/bin/env python3
"""Minimal IPS patch writer and applier, standard library only.

  ips.py make  SOURCE TARGET OUT.ips   same-size files only; records hold only the changed bytes
  ips.py apply SOURCE PATCH.ips OUT    plain and RLE records; a 3-byte truncation size after EOF is applied

IPS: "PATCH", then records (3-byte big-endian offset, 2-byte big-endian size, data;
size 0 = RLE: 2-byte count, 1 byte value), then "EOF". Offsets must be below 0x1000000.
A record may not start at 0x454F46 ("EOF"); the writer starts such a record one byte earlier.
"""
import sys

CHUNK = 1 << 20
EOF_OFS = 0x454F46
MAX_OFS = 0x1000000


def runs(src, tgt):
    """Yield (offset, bytes) for each run of changed bytes."""
    with open(src, 'rb') as a, open(tgt, 'rb') as b:
        pos, start, cur = 0, None, bytearray()
        while True:
            x, y = a.read(CHUNK), b.read(CHUNK)
            if len(x) != len(y):
                sys.exit('make: files differ in size')
            if not x:
                break
            if x != y:
                for i in range(len(x)):
                    if x[i] != y[i]:
                        if start is None:
                            start = pos + i
                        cur.append(y[i])
                    elif start is not None:
                        yield start, bytes(cur)
                        start, cur = None, bytearray()
            elif start is not None:
                yield start, bytes(cur)
                start, cur = None, bytearray()
            pos += len(x)
        if start is not None:
            yield start, bytes(cur)


def make(src, tgt, out):
    recs = []
    for ofs, data in runs(src, tgt):
        if ofs == EOF_OFS:  # cannot start a record here: start one byte earlier with the unchanged byte
            with open(tgt, 'rb') as f:
                f.seek(ofs - 1)
                data = f.read(1) + data
            ofs -= 1
        while data:
            part = data[:0xFFFF]
            if ofs + len(part) > MAX_OFS or ofs >= MAX_OFS:
                sys.exit('make: change at 0x%X is past the IPS 16 MB limit' % ofs)
            recs.append(ofs.to_bytes(3, 'big') + len(part).to_bytes(2, 'big') + part)
            ofs += len(part)
            data = data[0xFFFF:]
            if ofs == EOF_OFS and data:  # next record would start at "EOF": move one byte back into it
                ofs -= 1
                data = recs[-1][-1:] + data
    with open(out, 'wb') as f:
        f.write(b'PATCH' + b''.join(recs) + b'EOF')
    print('%d records, %d bytes' % (len(recs), 8 + sum(len(r) for r in recs)))


def apply(src, patch, out):
    p = open(patch, 'rb').read()
    if p[:5] != b'PATCH':
        sys.exit('apply: not an IPS file')
    buf = bytearray(open(src, 'rb').read())
    i = 5
    while True:
        if i + 3 > len(p):
            sys.exit('apply: no EOF marker')
        if p[i:i + 3] == b'EOF':
            i += 3
            break
        ofs = int.from_bytes(p[i:i + 3], 'big')
        size = int.from_bytes(p[i + 3:i + 5], 'big')
        i += 5
        if size:
            data = p[i:i + size]
            i += size
        else:
            n = int.from_bytes(p[i:i + 2], 'big')
            data = p[i + 2:i + 3] * n
            i += 3
        if ofs + len(data) > len(buf):
            buf.extend(bytes(ofs + len(data) - len(buf)))
        buf[ofs:ofs + len(data)] = data
    if len(p) - i == 3:
        del buf[int.from_bytes(p[i:i + 3], 'big'):]
    with open(out, 'wb') as f:
        f.write(buf)


def main(argv):
    if len(argv) == 4 and argv[0] == 'make':
        make(*argv[1:])
    elif len(argv) == 4 and argv[0] == 'apply':
        apply(*argv[1:])
    else:
        print(__doc__.strip())
        return 0 if argv[:1] in (['--help'], ['-h']) else 2
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
