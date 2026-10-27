#!/usr/bin/env python3
"""Turn a firmware ELF into a UF2 for the RP2040's ROM bootloader.

    uf2.py <elf> <uf2>
"""

import struct
import sys

FLASH_START = 0x10000000
FLASH_END = 0x11000000
FAMILY_RP2040 = 0xE48BFF56
BLOCK = 256


def segments(elf):
    """The ELF's loadable bytes, at their load addresses."""
    if elf[:4] != b"\x7fELF" or elf[4] != 1 or elf[5] != 1:
        sys.exit("not a little-endian 32-bit ELF")
    phoff, = struct.unpack_from("<I", elf, 28)
    phentsize, phnum = struct.unpack_from("<HH", elf, 42)
    for i in range(phnum):
        kind, offset, _, paddr, filesz = struct.unpack_from("<5I", elf, phoff + i * phentsize)
        if kind == 1 and filesz:  # PT_LOAD
            yield paddr, elf[offset : offset + filesz]


def main(elf_path, uf2_path):
    image = {}
    for addr, data in segments(open(elf_path, "rb").read()):
        if addr < FLASH_START or addr + len(data) > FLASH_END:
            sys.exit(f"{elf_path}: 0x{addr:08X}-0x{addr + len(data):08X} is outside flash")
        for i, b in enumerate(data):
            image[addr + i] = b

    blocks = sorted({a - a % BLOCK for a in image})
    out = bytearray()
    for n, base in enumerate(blocks):
        payload = bytes(image.get(base + i, 0xFF) for i in range(BLOCK))
        header = struct.pack(
            "<8I", 0x0A324655, 0x9E5D5157, 0x2000, base, BLOCK, n, len(blocks), FAMILY_RP2040
        )
        out += header + payload + bytes(476 - BLOCK) + struct.pack("<I", 0x0AB16F30)
    open(uf2_path, "wb").write(out)
    print(f"{uf2_path}: 0x{blocks[0]:08X}-0x{blocks[-1] + BLOCK:08X}, {len(blocks)} blocks")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(*sys.argv[1:])
