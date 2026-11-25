# CAM_03 Kernel Freeze Investigation

## Reproduced Failure

The user reported CAM_03 offline when detection started. Ethernet carrier was
lost even after switching from USB Ethernet to the laptop's native LAN port.
SSH, ping and the agent were unreachable over LAN; a search on the Pi's saved
MTC Wi-Fi did not find it either. This was not only a desktop status issue.

After power-cycle, the Pi was healthy at idle but old logs were unavailable.
Bounded persistent journaling was enabled on CAM_03 before repeating the test.
The user confirmed the official Raspberry Pi 27W/5A supply and approved a
60-second single-camera diagnostic run.

Diagnostic `SESSION_20261125_004` reproduced the freeze after approximately
40 seconds. After a second user power-cycle, the previous boot journal exposed
2,872 kernel warnings at `find_vma` / `hailo_vdma_buffer_map` in `hailo_pci`.
Last persisted observations still had carrier=1, no throttling flags and
temperature around 60 C; sampled voltages alone cannot exclude fast transients.

## Applied Change

A guarded PCIe-only mmap-lock backport was built from the installed Hailo
4.23.0 source against kernel `6.18.50+rpt-rpi-2712`. It was installed as a
kernel-specific module override, with original module/source backed up.
Firmware/HailoRT remain 4.23.0. Kernel, EEPROM, boot arguments and pairing
were not changed. The initramfs was inspected, not modified.

The code and administrator procedure are in the edge repository:
`docs/hailo_423_lock_backport.md` and
`systemd/install-hailo-423-lock-fix.sh`.

## Retest

`SESSION_20261125_005` completed a 60-second CAM_03-only run:

- 30 ready-state samples, frame age 98-336 ms.
- 136 authenticated events received by backend.
- Session ended `review_pending`; inference confirmed stopped.
- 95 hardware samples: Ethernet carrier remained 1, throttled flags stayed 0.
- Temperature 54.9-62.6 C; EXT5V 4.9178-5.14828 V.
- Zero matching VMA warnings on the current boot after the test.
- Loaded module srcversion `30DDE7EC2257F8EDD3C0D78`.

Only CAM_03 received the driver override. The desktop installer 0.2.4 is
unchanged and does not silently patch Pi kernel modules. Edge tests: 43 passed;
shell syntax and patch syntax passed; actual module build/load and hardware
retest passed. No diagnostic session remains active.

## Remaining Gates

Long-duration sessions, simultaneous cameras and persistence through a reboot
after module replacement have not yet been tested. The successful retest is
evidence for this targeted mitigation, not proof that every failure mode is
eliminated. Review kernel/Hailo package upgrades because the override is tied
to the current kernel/runtime combination. Keep the original module backup.

The laptop was on MTC Wi-Fi for this investigation. Return it to the intended
shared network before operating other Wi-Fi cameras, then run Scan LAN.
