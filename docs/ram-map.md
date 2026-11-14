# RAM map

Rockman X3 (Japan), Sega Saturn, T-1210G V1.001. The IP header also gives the date 19960325 and area J. Track 01 holds 173 files.

Addresses are Saturn bus addresses. Work RAM-H starts at 0x06000000. All entries were read in the program files or in save states. An entry says so if it was also seen in Mednafen 1.32.1 (one observation), is not proven, or comes from memory. [how-it-works.md](how-it-works.md) gives the context.

## Program images

| Address | What |
|---|---|
| 0x06010000 | `0X3_SS.BIN` load and start address (IP first-read address). The image ends at 0x060424A0. |
| 0x06010070 | Main function. The entry calls it from 0x0601003C. |
| 0x06044000 | `X3_SS1.BIN` (folder OV) load address. Its file table entry is at 0x06017ADC. |
| 0x060172A0-0x060178CF | File table for folders D1, D2, D3: 99 entries of 16 bytes {dir, name, dest, size}. |
| 0x060178D4-0x06017AEF | Overlay table (folder OV): 27 entries of 20 bytes {dir, name, run, stage, max}. |

## VDP2 register shadows

The game keeps RAM copies of the VDP2 registers (shadows) and copies them to VDP2.

| Address | What |
|---|---|
| 0x06040C58 | Shadow 1: copy of VDP2 registers 0x00-0xDF (same layout). |
| 0x06040C54 | Destination pointer for shadow 1 = 0x25F80000. |
| 0x06040C78 | BGON in shadow 1 (layer enable). 0x0007 on the intro stage. |
| 0x06040D28 | WCTLA in shadow 1 (window control). 0x0202 on the intro stage. |
| 0x06040D38 | Not registers: rotation parameter tables (0x80 stride). |
| 0x06041B54 | Shadow 2: copy of VDP2 registers 0xE0-0x11F, in six blocks. |
| 0x06041B58 | CRAOFA shadow (register 0xE4). Bits 0-2: NBG0 CRAM page. The patch makes it 0x0001. A RAM write of this value was tested in Mednafen. |
| 0x06041B94 | Dirty bits for shadow 2. Bit 0x80 = block 0xE0-0xEF (includes CRAOFA). |
| 0x06041B9C | CRAM slot table, 8 longs. The start-up code clears it. |
| 0x06042384-0x06042398 | Destination pointers for the shadow 2 blocks (0x25F800E0 to 0x25F80110). |

## Functions

| Address | What |
|---|---|
| 0x06033370 | Copies shadow 1 to VDP2 registers. |
| 0x060334C8 | Copies the dirty blocks of shadow 2 to VDP2 registers. |
| 0x06033448 | Word copy (r4 destination, r5 source, r6 bytes). |
| 0x06016560 | Sets a dirty bit for shadow 2. |
| 0x060348F0 | Shadow 2 defaults. Clears the CRAOFA fields. Runs last at start-up. Contains the patch site 0x06034A08. |
| 0x06034A08 | Patch site: second NBG0 clear of CRAOFA. |
| 0x06033C24 | Calls 0x060348F0 and clears the slot table 0x06041B9C. |
| 0x0603A50C | Sets the CRAM page of each layer in CRAOFA/CRAOFB, and BGON bits (r4 layer mask, r5 page, r6 flag). |
| 0x06033718 | CRAM allocator. Only caller of 0x0603A50C. Returns 0x25F00000 + slot x 0x200. |
| 0x0601398C | Clears CRAM and calls the allocator. Main calls it at 0x0601009C. |
| 0x06013388 | Start of the chain to 0x060348F0 (0x06013388, 0x06013808, 0x060135A4, 0x06032D08, 0x06033C24). Main calls it at 0x060100A8. |
| 0x060321C0 | Per-layer setup (BGON, CHCTLA/B). |
| 0x06033838 | Sets the priority registers PRINA, PRINB, PRIR in shadow 2. |
| 0x0603480C | Sets the colour offset registers. |
| 0x06035860, 0x060359B0 | Set window 0. |

## Colour data

| Address | What |
|---|---|
| 0x060E0320 | RAM copy of CRAM 0x000-0x2FF (CRAM mirror). |
| 0x060E0500 | Border palette row 0x0F inside the CRAM mirror. The game writes it again in less than 0.5 s (seen in Mednafen). |
| 0x060993B0 | Border palette row in `X3_SS1.BIN` (file offset 0x553B0). Full-motion video uses this area as a buffer. That this copy feeds CRAM is not proven. |

## VDP2 hardware (for reference)

| Address | What |
|---|---|
| 0x25F80000 | VDP2 registers. |
| 0x25F800E4 | CRAOFA (CRAM offset for NBG0-NBG3, 3 bits each). From memory, not checked in the VDP2 manual. |
| 0x25F00000 | CRAM. In mode 1 (2048 colours, RGB555), page n starts at colour n x 0x100. |

## Intro stage values (save states)

TVMD 0x8010 (320 x 240), RAMCTL 0x1000 (CRAM mode 1), BGON 0x0007, CHCTLA 0x0404, CRAOFA 0x0000, PRINA 0x0407.
The NBG0 map page is at VRAM 0x40000. The border characters 0x760-0x7DE are at VRAM 0xEC00-0xFBDF.
