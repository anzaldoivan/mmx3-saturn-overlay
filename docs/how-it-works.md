# How it works

## The border

The game uses a 320 x 240 screen and shows play in a 256 x 224 window at (32, 8). The border fills the 32-pixel strips at the left and right, and the 8-line strips at the top and bottom. A [Sonic Retro thread](https://forums.sonicretro.org/threads/43927/) from 2025 found that the border is an overlay, and that a 4:3 picture shows when one layer is hidden. The edges of that picture have graphic errors, so the patch keeps the overlay and makes it black.

The border is on VDP2 layer NBG0. Its cells have 16 colours, and every cell uses palette 15. On the intro stage NBG0 holds only the border, and its middle is transparent. The register CRAOFA (0xE4) holds the CRAM page of each layer. In the game it is 0x0000, so NBG0 reads page 0, colours 0x0F1-0x0FF. The same palette row on page 1, colours 0x1F1-0x1FF, is all 0x0000, which is black.

## The edit

The game does not write most VDP2 registers directly. It keeps copies in RAM (shadows, listed in [ram-map.md](ram-map.md)) and copies them to VDP2. The CRAOFA shadow is at 0x06041B58. Two functions write it, 0x0603A50C and 0x060348F0, and both run once at start-up. 0x060348F0 runs last and clears the NBG0 field two times. The second clear, at 0x06034A08, is the last NBG0 write at start-up. The patch changes this clear so that it also adds 1.

The edit is in `0X3_SS.BIN` at file offset 0x24A08. Register r13 holds 0x0000FFF0.

| Address | Before | | After | |
|---|---|---|---|---|
| 0x06034A08 | `622D` | `extu.w r2,r2` | `22D9` | `and r13,r2` |
| 0x06034A0A | `22D9` | `and r13,r2` | `7201` | `add #1,r2` |

r2 holds the CRAOFA value, sign-extended. `and r13,r2` also clears the upper bits, so the old `extu.w` had no effect and the `add` takes its place. CRAOFA becomes (old value AND 0xFFF0) + 1. The NBG0 field becomes 1 and the other fields do not change. The code size is the same, so no free space is needed. A soft reset runs the start-up code again and gives the same result.

## The disc sector

The edit is in Track 01, sector LBA 103. The track is MODE1 with 2352 bytes for each sector, and the user data starts at byte 16. Each sector holds EDC/ECC check data, which must be calculated again when the data changes. Real hardware can show read errors when the check data is wrong. Emulators often do not check it.

- EDC is a CRC-32 over sector bytes 0x000-0x80F, polynomial 0x8001801B (bit-reversed), stored little-endian at 0x810.
- ECC follows ECMA-130 Annex A. P parity over 0x00C-0x81B (86 x 24) goes to 0x81C. Q parity over 0x00C-0x8C7 (52 x 43) goes to 0x8C8.

`tools/cdpatch.py` does this calculation. As a test, it calculated the EDC/ECC of 160 sectors of the original track again, and all 160 were equal to the disc. The patched track differs from the original in 59 bytes, all in LBA 103. These are the 4 code bytes and 55 EDC/ECC bytes.

## How it was found

Capstone disassembled the two program files, `0X3_SS.BIN` and `X3_SS1.BIN`. This showed the shadows, but no write to CRAOFA. Save states from Ymir and Mednafen then gave the live VDP2 registers, VRAM and CRAM. The live registers were equal to the shadows. The layer, the palette and the black page were found in this data.

For a first test, 0x0001 was written to the CRAOFA shadow in a Mednafen save state on the intro stage. The border became black 13-21 s later and stayed black. The test ran for about 40 s, with scrolling, firing and the weapon menu. One write was sufficient, and nothing wrote the field again. The delay is probably because the game copies that register block only when another write marks the block as changed.

## Other screens

The new value applies from start-up on every screen. A script compared 51 Mednafen save states with NBG0 on page 0 and on page 1.

- Intro stage, attract story, video interludes: all border dots become black, as wanted.
- Fades: 16 dots change colour, but the screen shows black there.
- Boot logo and some other frames: pages 0 and 1 hold the same colours.
- Title, menu and loading screens: NBG0 has no visible dots.
- Full-motion video uses NBG0 as an RGB bitmap. RGB colour does not use CRAOFA (from memory, not checked in the VDP2 manual).
- Not seen: the other stages, boss screens, stage select, password, options, ending, game over and continue. A graphic on NBG0 other than the border can show black or with wrong colours there.

## Options not used

- Hide the border layer. The hidden picture has graphic errors at the edges, and the back screen cannot be clipped.
- Clip with a window. The game already uses window 0 on several layers. Window 1 is free, but it needs a code hook.
- Make the border palette black. The palette is shared, and in a RAM test the game wrote the row again from other copies in less than 0.5 s.
- Patch only the first NBG0 clear, at 0x06034988. The second clear sets the field to 0 again.
