# Network Modes and Installer 0.2.4 Delivery

## Implemented

- Explicit Direct LAN / Location DHCP selection in Devices > Network setup.
- Root-owned profile helper stops Ethernet DHCP serving before enabling a site
  DHCP-client profile. Fixed permitted actions; no shell commands from requests.
- Three-minute systemd rollback, immediate activation-failure rollback, and a
  boot restore service for unconfirmed changes. No DHCP-server auto fallback
  based only on failure to receive a location lease.
- Explicit confirmation must arrive on the new Ethernet interface, including
  requests addressed through mDNS. A Wi-Fi-only check cannot confirm Ethernet.
- Assessment start is blocked while a network transition is unconfirmed.
  Network changes are blocked during preparing/running/stopping sessions.
- Existing device credentials verify both the camera UUID and the backend's
  ownership before saving changed device/backend URLs. Pairing is not reset.
- Backend callbacks use the OS-selected route to each Pi, including initial
  pairing and session start. No gateway-address assumption.
- Bounded discovery, UUID deduplication, paired `.local` hostname probes and
  visible Devices-page recovery scans every 45 seconds when idle.
- Versioned installer includes Electron, FastAPI executable, migrations, export
  dependencies, icons, an offline edge Git bundle and update instructions.
- Windows backend firewall rule is program-specific, TCP 8000, local-subnet
  sources only, all profiles (direct Ethernet is often classified Public).

## Artifact

`desktop/installer/release-0.2.4/ERGoSIGHT-Setup-0.2.4.exe`

- Windows x64 NSIS, per-machine, administrator approval required.
- Size: 135,583,389 bytes.
- SHA256: `249F8747992748FDFF3A8321665ABF0E505E218759A4FBDB6F404F768D943E65`.
- Authenticode: NotSigned. Distribute only through a trusted channel and verify
  the checksum; a signing certificate was not available for this build.
- Bundled edge commit: `f655446`; agent API version 0.2.4.
- Offline bundle includes no tracked credential/state files; checked both
  current Git paths and history for `.env`, `credentials.txt`, `edge_state.json`.

## Verified

- Backend suite: 55 passed. Edge suite: 42 passed. Desktop Node suite: 4 passed.
- Desktop lint/build and network installer shell syntax checks passed.
- Browser tests covered mode selection, confirmation, missing-helper disabled
  states, two-way reconnect requests, and 1120x720 / 1440x900 layouts. Screenshots
  were inspected; the final pass fixed selected-network text contrast and label
  positioning. No real network mutation was performed by browser fixtures.
- Packaged backend started on port 18004 with an isolated fresh SQLite profile.
  Migrations, registration/login and authenticated PDF/Excel/ZIP exports passed;
  unauthenticated report access was rejected. The smoke process was stopped.
- ASAR main/preload/profile modules and built frontend assets matched source.
  Packaged backend matched the built executable; report fonts/logo and all four
  offline edge-update resources were present and compared to build inputs.
- Agent `f655446` and helper installed on CAM_02 over `10.55.2.1`, CAM_03 over
  `10.55.3.1`, and CAM_01 through its existing Wi-Fi `192.168.1.38`.
- All three returned authenticated `available=true, mode=direct, pending=false`.
  Services remained active. Helpers and sudoers are root-owned; startup restore
  is enabled. Camera UUIDs/credentials and active Ethernet modes were preserved.
- No active assessment existed before restarts. No kernel/EEPROM changes.

## Manual Installation and Remaining Gates

The local unpacked 0.2.4 desktop was started with the existing account profile.
The Windows setup installer itself has not been executed/approved by the agent.
The unpacked backend listens on 8000, but actual Pi-to-laptop callbacks time out
under the current firewall. The installer-added rule requires Windows admin/UAC
approval. Unit tests of ownership challenge and two-way reconnection passed,
but this does not substitute for that real firewall/installation gate.

Operator next steps:

1. Close the portable/unpacked desktop to release its instance lock and backend.
2. Run the setup artifact above and approve UAC. Open the installed shortcut,
   not the old unpacked executable; firewall rules refer to the installed path.
3. Sign in if requested, then Devices > Scan LAN. Do not reset pairing.
4. With a router/DHCP server available, stop assessments, apply Location mode,
   move the cable, scan and confirm on the Ethernet address within three minutes.

Physical cable transfer to a router/DHCP server, real timer/reboot rollback,
clean-second-laptop install, and simultaneous inference/long soak remain untested.
DHCP-failure, rollback and reboot restoration paths were tested with mocked system
commands, not represented as hardware acceptance. Network mode is not switched
automatically during deployment. See [operator guide](network_setup_0.2.4.md).
