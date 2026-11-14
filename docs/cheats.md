# Cheat codes

The same change can be made in RAM with a cheat code, without a patched disc. Do not use a code together with the patched disc.

Both codes write 0x0001 (16 bits) to 0x06041B58, the game's copy of the VDP2 register CRAOFA. The border does not change at once. The colour changes when the game next copies this register block to VDP2, which can take some seconds. In the Mednafen save-state test it took 13-21 s.

The codes write the full CRAOFA word, so the NBG1-NBG3 fields become 0. These fields were 0 on all screens in the tests. The disc patch changes only the NBG0 field.

## Action Replay

```
16041B58 0001
```

Not tested on hardware or on a real Action Replay cartridge. A master code may be necessary. None is confirmed for this game.

## Mednafen

Put this line in the Saturn cheat file (`ss.cht`), below the header for the game. Mednafen 1.32.1 uses the header `[8551bb52f6c321890b88ddbe801610f7]` for this disc.

```
R A 2 B 0 06041b58 0001 X3 black border
```

The fields are R (replace the value before each vblank), A (active), 2 (length in bytes), B (big-endian), a reserved 0, the address, the value and a name.

Not tested as a cheat file. The Mednafen test wrote the value one time into a save state.
