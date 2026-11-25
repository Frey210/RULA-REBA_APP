# Two Direct LAN Cameras: 2026-11-25

## Confirmed Cause

Both CAM_02 and CAM_03 advertised `10.55.0.1/24`. The laptop received
`10.55.0.132` and `10.55.0.125` on separate Ethernet adapters. Windows had
two competing routes to the same subnet; ordinary HTTP traffic reached one Pi.
Those `.132` and `.125` addresses belonged to the laptop, not the cameras.
Interface-bound probes confirmed two different device UUIDs behind the same IP.

The desktop also launched all subnet probes concurrently with 450 ms timeouts.
A reproduction missed both reachable cameras under that load. Discovery now
probes gateway addresses first with 1500 ms timeouts, then other addresses in
batches of at most 32. Other hosts remain discoverable.

## Applied Configuration

| Device | Pi address | Laptop address at verification | Laptop adapter |
| --- | --- | --- | --- |
| CAM_02 | `10.55.2.1:8765` | `10.55.2.132` | Ethernet 2 |
| CAM_03 | `10.55.3.1:8765` | `10.55.3.125` | Ethernet |

- NetworkManager persistent profiles and live addresses use distinct subnets.
- Each Pi's DHCP pool uses its own `.100` through `.200` range.
- No Ethernet default gateway or DNS is advertised; Wi-Fi internet is unchanged.
- The legacy `.0.1` address was removed after DHCP release/renew on the laptop.
- Device URLs in the installed profile were updated only after authentication
  and UUID verification. Pairing credentials and ownership were preserved.
- Each Pi's saved backend callback now uses its corresponding laptop address.
- Configuration and installed SQLite backups were made before changes.
- No active assessment existed. No kernel, EEPROM, passwords or ownership changed.

Future provisioning derives `10.55.N.1/24` from `EDGE_CAM_ID=CAM_N`, accepting
camera numbers 1 through 254. Every device must have a unique technical ID.
The installer's explicit `EDGE_DIRECT_LAN_ADDRESS` environment override accepts
RFC1918 `.1/24` addresses. Network status reports the actual Ethernet address.
Both connected agents are deployed at edge commit `9f2f3a5`.

## Verification

- Both public pairing endpoints answered with distinct expected UUIDs.
- Both authenticated stream status endpoints reported `camera_available=true`.
- Both authenticated snapshot endpoints returned JPEG frames (30,113 / 45,225
  bytes during one check); photos were not added to Git.
- Both Pi services are active; persistent profiles contain only their new subnet.
- The actual desktop discovery functions found both devices in one LAN scan.
- Both Pis reached the running laptop backend version endpoint with HTTP 200.
- 14 focused edge tests, 2 desktop Node tests, ESLint and shell syntax checks pass.
- Packaged Electron main code was compared byte-for-byte with source.

## Desktop Build and Operator Steps

The updated unpacked desktop was built and launched at:

`desktop/installer/dual-lan-0.2.3/win-unpacked/ERGoSIGHT.exe`

This is a local 0.2.3 hotfix build, not a newly versioned setup installer. The old
`preview-0.2.3` executable and setup installer do not contain the scan fix.

1. Use the newly opened desktop; sign in if asked.
2. Open Devices and select Scan LAN. Both cameras should appear without resetting
   pairing. If probing manually, use the Pi addresses above, not the laptop IPs.
3. Create a new assessment and select both CAM_02 and CAM_03 before starting.

Separate direct cables require separate subnets. For multiple Pis on a shared
switch, use a router/DHCP network instead; do not attach these independent DHCP
servers to the same switch. Laptop DHCP addresses can change on another laptop;
refresh device setup/pairing through the normal owning backend when moving it.

## Not Yet Verified

No simultaneous detection session, inference throughput, long-running soak,
cross-camera identity accuracy, reboot or power-cycle test was performed here.
CAM_02's OS clock is still behind the client date; this change did not alter the
clock. Existing session capture clock anchoring is separate from OS time.

## CAM_01 Follow-Up

After replacing CAM_03 with CAM_01 on the laptop Ethernet port:

- Confirmed hostname `ergoquipt-rr` and UUID
  `886cd0e0-8762-40e9-847d-0932fb6db4a5` through its trusted SSH key and pairing info.
- Upgraded agent from `fbd2b4e` to `9f2f3a5` via the local Git bundle.
- Backed up network configuration, `.env`, and edge state before migration.
- Persistent and live LAN configuration now use `10.55.1.1/24`; DHCP pool is
  `10.55.1.100` through `.200`. Removed the old `10.55.0.1` address.
- Laptop Ethernet renewed to `10.55.1.125`; CAM_02 remains on Ethernet 2 with
  laptop address `10.55.2.132`. No overlapping camera subnets remain.
- Updated saved backend callback to `http://10.55.1.125:8000`; the Pi reached
  that backend with HTTP 200.
- Existing CAM_01 credentials were present and successfully authenticated.
  Contrary to the earlier deployment's legacy state, no pairing reset or new
  pairing is required now. Updated its stored device URL only after UUID and
  credential verification, with an installed database backup.
- The authenticated preview returned a JPEG (26,177 bytes in one check), and
  stream status reported `camera_available=true`. The first preview request
  immediately after service restart returned 503 during warm-up; retry passed.
- Service remains active and enabled; kernel/EEPROM and hostname are unchanged.

CAM_03 is unplugged during this follow-up. Simultaneous detection and reboot
remain untested; no assessment was started automatically.

The follow-up scan also found CAM_01 over Wi-Fi at `192.168.1.38`. Discovery now
deduplicates by device UUID, preserving the gateway result found first, so the
same Pi does not appear twice or overwrite its LAN address with its Wi-Fi URL.
The latest local unpacked build includes this fix at
`desktop/installer/dual-lan-identity-0.2.3/win-unpacked/ERGoSIGHT.exe`.
