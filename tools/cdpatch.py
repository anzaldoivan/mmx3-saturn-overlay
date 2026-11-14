#!/usr/bin/env python3
"""Patch files inside a MODE1/2352 data track (.bin) through its ISO9660 directory; regenerate EDC/ECC.

  cdpatch.py selftest TRACK [N]          recompute EDC/ECC of N (default 128) spread sectors, compare with stored
  cdpatch.py apply EDITS TRACK OUT       copy TRACK to OUT, apply EDITS to OUT, regenerate touched sectors' EDC/ECC
  cdpatch.py verify EDITS ORIG PATCHED   PATCHED differs from ORIG only in edited bytes + their sectors' EDC/ECC;
                                         touched sectors' EDC/ECC valid; re-extracted file holds the new bytes
  cdpatch.py extract TRACK PATH OUT      write one file (e.g. OV/X3_SS1.BIN) from the track

EDITS: text, '#' comments; lines `track <sha1>` (whole track before) and
`edit <ISO path> <file offset hex> <file sha1 before> <old hex> <new hex>`.
EDC: CRC-32 over sector bytes 0x000-0x80F, poly 0x8001801B bit-reversed (0xD8018001), stored LE at 0x810.
ECC: ECMA-130 Annex A RSPC; P over 0x00C-0x81B (86 x 24) -> 0x81C; Q over 0x00C-0x8C7 (52 x 43) -> 0x8C8."""
import hashlib, shutil, struct, sys

SS, UD = 2352, 16  # raw sector size, user-data offset in a MODE1 sector

EDC_T = []
for i in range(256):
    e = i
    for _ in range(8):
        e = (e >> 1) ^ (0xD8018001 if e & 1 else 0)
    EDC_T.append(e)
F_LUT, B_LUT = [0] * 256, [0] * 256
for i in range(256):
    j = (i << 1) ^ (0x11D if i & 0x80 else 0)
    F_LUT[i] = j
    B_LUT[i ^ j] = i


def edc(b):
    e = 0
    for x in b:
        e = (e >> 8) ^ EDC_T[(e ^ x) & 0xFF]
    return e


def ecc_block(src, major_count, minor_count, major_mult, minor_inc):
    size = major_count * minor_count
    out = bytearray(2 * major_count)
    for major in range(major_count):
        index = (major >> 1) * major_mult + (major & 1)
        a = b = 0
        for _ in range(minor_count):
            t = src[index]
            index += minor_inc
            if index >= size:
                index -= size
            a ^= t
            b ^= t
            a = F_LUT[a]
        a = B_LUT[F_LUT[a] ^ b]
        out[major] = a
        out[major + major_count] = a ^ b
    return out


def regen(sec):
    """Return a copy of a MODE1 raw sector with EDC, zero field and ECC P/Q recomputed."""
    s = bytearray(sec)
    assert s[15] == 1, 'not a MODE1 sector'
    struct.pack_into('<I', s, 0x810, edc(s[0:0x810]))
    s[0x814:0x81C] = bytes(8)
    s[0x81C:0x8C8] = ecc_block(s[0xC:0x81C], 86, 24, 2, 86)
    s[0x8C8:0x930] = ecc_block(s[0xC:0x8C8], 52, 43, 86, 88)
    return bytes(s)


def rd(f, lba, n=1):
    f.seek(lba * SS)
    return f.read(n * SS)


def find(f, path):
    """ISO9660 lookup -> (extent LBA, size). Path like 'OV/X3_SS1.BIN' (no version)."""
    pvd = rd(f, 16)[UD:UD + 2048]
    assert pvd[1:6] == b'CD001', 'no ISO9660 PVD at LBA 16'
    lba, size = struct.unpack_from('<I', pvd, 156 + 2)[0], struct.unpack_from('<I', pvd, 156 + 10)[0]
    for part in path.strip('/').upper().split('/'):
        n = (size + 2047) // 2048
        raw = rd(f, lba, n)
        d = b''.join(raw[i * SS + UD:i * SS + UD + 2048] for i in range(n))
        o, hit = 0, None
        while o < len(d):
            ln = d[o]
            if ln == 0:
                o = (o // 2048 + 1) * 2048
                continue
            nm = d[o + 33:o + 33 + d[o + 32]].decode('ascii', 'replace').split(';')[0]
            if nm == part:
                hit = struct.unpack_from('<I', d, o + 2)[0], struct.unpack_from('<I', d, o + 10)[0]
                break
            o += ln
        assert hit, 'not found: %s in %s' % (part, path)
        lba, size = hit
    return lba, size


def read_file(f, path):
    lba, size = find(f, path)
    n = (size + 2047) // 2048
    raw = rd(f, lba, n)
    return b''.join(raw[i * SS + UD:i * SS + UD + 2048] for i in range(n))[:size]


def parse(path):
    track, edits = None, []
    for ln in open(path):
        w = ln.split('#')[0].split()
        if not w:
            continue
        if w[0] == 'track':
            track = w[1].lower()
        elif w[0] == 'edit':
            edits.append((w[1], int(w[2], 16), w[3].lower(), bytes.fromhex(w[4]), bytes.fromhex(w[5])))
            assert len(edits[-1][3]) == len(edits[-1][4]), 'old/new length differ'
    return track, edits


def sha1_file(p):
    h = hashlib.sha1()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 22), b''):
            h.update(c)
    return h.hexdigest()


def targets(f, edits):
    """-> list of (track byte position, old byte, new byte) for every edited byte; checks file sha1."""
    out = []
    for path, off, sha, old, new in edits:
        lba, size = find(f, path)
        data = read_file(f, path)
        assert hashlib.sha1(data).hexdigest() == sha, '%s sha1 %s != %s' % (path, hashlib.sha1(data).hexdigest(), sha)
        assert off + len(old) <= size
        for k in range(len(old)):
            p = off + k
            out.append(((lba + p // 2048) * SS + UD + p % 2048, old[k], new[k]))
    return out


def selftest(track, n):
    with open(track, 'rb') as f:
        f.seek(0, 2)
        total = f.tell() // SS
        lbas = sorted(set(int(i * (total - 1) / (n - 1)) for i in range(n)))
        ok = bad = skip = 0
        for lba in lbas:
            s = rd(f, lba)
            if s[15] != 1:
                skip += 1
                continue
            if regen(s) == s:
                ok += 1
            else:
                bad += 1
                print('MISMATCH lba %d' % lba)
    print('selftest: %d sectors of %d checked, %d equal, %d differ, %d not MODE1' % (len(lbas), total, ok, bad, skip))
    return bad == 0 and ok >= 100


def apply(edits_path, track, out):
    tsha, edits = parse(edits_path)
    if tsha:
        got = sha1_file(track)
        assert got == tsha, 'track sha1 %s != %s' % (got, tsha)
    shutil.copyfile(track, out)
    with open(out, 'r+b') as f:
        t = targets(f, edits)
        secs = set()
        for pos, o, nw in t:
            f.seek(pos)
            assert f.read(1)[0] == o, 'old byte mismatch at track 0x%X' % pos
            f.seek(pos)
            f.write(bytes([nw]))
            secs.add(pos // SS)
        for lba in sorted(secs):
            s = regen(rd(f, lba))  # rd() seeks and reads: seek again before the write
            f.seek(lba * SS)
            f.write(s)
    print('applied %d bytes in %d sector(s) %s -> %s' % (len(t), len(secs), sorted(secs), out))


def verify(edits_path, orig, patched):
    _, edits = parse(edits_path)
    with open(orig, 'rb') as fo, open(patched, 'rb') as fp:
        t = targets(fo, edits)
        want = {pos for pos, o, nw in t if o != nw}
        secs = {pos // SS for pos, o, nw in t}
        allowed = set(want)
        for lba in secs:
            allowed |= set(range(lba * SS + 0x810, lba * SS + 0x814)) | set(range(lba * SS + 0x81C, lba * SS + 0x930))
        diff, base, chunk = set(), 0, SS * 4096
        fo.seek(0)
        fp.seek(0)
        while True:
            a, b = fo.read(chunk), fp.read(chunk)
            assert len(a) == len(b), 'size differs'
            if not a:
                break
            if a != b:
                for i in range(0, len(a), SS):
                    if a[i:i + SS] != b[i:i + SS]:
                        diff |= {base + i + k for k in range(SS) if a[i + k] != b[i + k]}
            assert len(diff) < 1 << 20, 'too many differences'
            base += len(a)
        stray = sorted(diff - allowed)
        missing = sorted(want - diff)
        valid = all(regen(rd(fp, lba)) == rd(fp, lba) for lba in secs)
        newok = True
        for path, off, sha, old, new in edits:
            data = read_file(fp, path)
            newok &= data[off:off + len(new)] == new
            print('%s: patched sha1 %s, bytes at 0x%X = %s' % (path, hashlib.sha1(data).hexdigest(), off, data[off:off + len(new)].hex()))
    print('verify: %d differing bytes (%d user-data edits, %d other), stray %d, missing %d, EDC/ECC valid %s, new bytes %s' % (
        len(diff), len(diff & want), len(diff - want), len(stray), len(missing), valid, newok))
    return not stray and not missing and valid and newok


def main():
    c = sys.argv[1] if len(sys.argv) > 1 else '--help'
    if c in ('-h', '--help'):
        print(__doc__)
        sys.exit(0)
    if c not in ('selftest', 'apply', 'verify', 'extract'):
        sys.exit(__doc__)
    if c == 'selftest':
        r = selftest(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 128)
    elif c == 'apply':
        apply(*sys.argv[2:5])
        r = True
    elif c == 'verify':
        r = verify(*sys.argv[2:5])
    elif c == 'extract':
        with open(sys.argv[2], 'rb') as f:
            open(sys.argv[4], 'wb').write(read_file(f, sys.argv[3]))
        r = True
    sys.exit(0 if r else 1)


if __name__ == '__main__':
    main()
