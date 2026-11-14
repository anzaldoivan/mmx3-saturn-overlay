# Tools

Three Python 3 scripts. They need only the standard library and contain no game data. `--help` prints the usage.

## bps.py and ips.py

Make and apply BPS and IPS patches.

```
python3 tools/bps.py apply SOURCE PATCH.bps OUT
python3 tools/bps.py make  SOURCE TARGET OUT.bps [--meta TEXT]
python3 tools/ips.py apply SOURCE PATCH.ips OUT
python3 tools/ips.py make  SOURCE TARGET OUT.ips
```

- `make` works only on two files of the same size.
- `bps.py apply` supports all four BPS actions and checks the three CRC32 values (source, target, patch). With a wrong source file it stops with "source CRC mismatch" and writes no output.
- `ips.py apply` does not check the source file. IPS offsets must be below 16 MB.

To patch the disc from the command line:

```
python3 tools/bps.py apply "<Track 01>.bin" patch/x3-border-a2.bps "<patched Track 01>.bin"
```

## cdpatch.py

Changes files inside a MODE1/2352 data track (`.bin`) through its ISO9660 directory. It calculates the EDC/ECC of each changed sector again.

```
python3 tools/cdpatch.py apply    EDITS TRACK OUT
python3 tools/cdpatch.py verify   EDITS ORIG PATCHED
python3 tools/cdpatch.py extract  TRACK PATH OUT
python3 tools/cdpatch.py selftest TRACK [N]
```

- `apply` checks the SHA-1 of the track, the SHA-1 of each file and the old bytes before it writes.
- `verify` checks that only the edited bytes and their EDC/ECC changed, and that the EDC/ECC is valid.
- `extract` copies one file out of the track. PATH is the ISO9660 path, for example `OV/X3_SS1.BIN`.
- `selftest` calculates the EDC/ECC of N sectors of an original track again (128 by default) and compares them with the stored values.

`patch/x3-border-a2.edits` is the edit list for this patch. `apply` with this list gives the same file as the three patch files.
