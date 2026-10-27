/* The flash layout is in README.md: boot2, then the firmware, up to RMK's storage in the last
   8 sectors of 2 MB (FLASH_SIZE and STORAGE in src/central.rs). */
MEMORY
{
  BOOT2 : ORIGIN = 0x10000000, LENGTH = 0x100
  FLASH : ORIGIN = 0x10000100, LENGTH = 2048K - 0x100 - 32K
  RAM   : ORIGIN = 0x20000000, LENGTH = 256K
}
