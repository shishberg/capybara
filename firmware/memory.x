/* nice!nano v2 flash, with the Adafruit nRF52 bootloader and the S140 SoftDevice it needs
   to start any app (see README.md, "Flash layout"):

     0x00000 - 0x00FFF  MBR
     0x01000 - 0x25FFF  SoftDevice S140 6.1.1   never written
     0x26000 - 0xEBFFF  this firmware
     0xEC000 - 0xF3FFF  RMK's storage (STORAGE in src/central.rs), the 32 KB under the bootloader
     0xF4000 -          the bootloader and its settings, never written

   uf2.py refuses to write a UF2 with any byte outside 0x26000 - 0xEC000. */
MEMORY
{
  FLASH : ORIGIN = 0x00026000, LENGTH = 0xEC000 - 0x26000
  RAM   : ORIGIN = 0x20000008, LENGTH = 256K - 8
}
