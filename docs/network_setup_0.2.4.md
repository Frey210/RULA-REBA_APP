# ERGoSIGHT 0.2.4: Network Setup

## Install Desktop

Run `ERGoSIGHT-Setup-0.2.4.exe` with administrator approval. Electron, the Python
backend, SQLite migrations, PDF/Excel/ZIP dependencies, icons and the offline Pi
update bundle are included; Node, Python, Excel and internet are not required on
the operator laptop. Existing account data, photos and pairing secrets stay in
`%APPDATA%\ergosight-desktop`. Do not delete that folder when upgrading.

The installer allows its backend executable on TCP 8000 from local subnets,
including Windows Public Ethernet profiles. It does not open unrestricted
internet access or require Windows Internet Connection Sharing. Corporate
firewall policy may still require administrator approval.

## Update Existing Pi Agents Once

Network mode switching requires both desktop and agent 0.2.4, plus the root-owned
network helper. The Windows installer cannot silently authenticate to a new Pi.
An administrator performs this step once; ordinary operators then use the UI.

The installed application includes `resources/edge-update/` containing
`ergosight-edge.bundle`, `edge-commit.txt`, `update-edge.sh` and this guide.
Copy the bundle and update script into a directory on the Pi through SSH/SCP,
verify the Pi's SSH host key, stop active assessments, then run on that Pi:

```bash
cd ~/ergosight-update
bash update-edge.sh
```

The script targets the existing `~/RULA-REBA_Detection_HailoAI` installation,
backs up `.env` and state, merges only fast-forward, installs the network helper,
and restarts the agent. It does not flash storage, change the kernel/EEPROM,
reset credentials or change the currently selected Ethernet mode. Fresh Pi OS
provisioning remains a separate administrator task.

## Direct Ethernet

1. Connect one Pi directly to a laptop Ethernet port. Set laptop IPv4 to DHCP.
2. Open Devices and select Scan LAN. Pair once if the device is new.
3. Use the discovered camera in a new assessment.

CAM_01 uses `10.55.1.1`, CAM_02 `10.55.2.1`, CAM_03 `10.55.3.1`. Each Pi gives
the corresponding laptop adapter a `.100` through `.200` address without a
default gateway/DNS. Separate direct cables require separate subnets. Do not
attach Direct-mode Pi DHCP servers to a shared location switch.

## Location Ethernet: Router or Switch

1. Stop assessments using that Pi. While still connected, open Devices,
   Scan LAN, then Network setup for the paired camera.
2. Choose Ethernet mode: Location router / switch (DHCP), then Apply mode.
3. Move the Pi cable to the location router/switch. Connect the laptop to that
   LAN by Ethernet or Wi-Fi. A router or DHCP server must exist; a switch alone
   does not assign IP addresses.
4. Run Scan LAN. Open Network setup on the new Ethernet address and select
   Keep Ethernet mode within three minutes. If necessary, Probe IP using the
   router's DHCP lease list to select the Ethernet address rather than Wi-Fi.
5. Create a new assessment after both directions are verified.

The Pi stops its Ethernet DHCP server before requesting a location lease.
The new mode is retained only after explicit confirmation through the Ethernet
interface; confirmation over the Pi's Wi-Fi address is rejected. Failure to
activate DHCP immediately restores the previous profile. An unconfirmed change
rolls back after three minutes; reboot also attempts to restore the previous
profile before starting the agent. Reconnect the direct cable if rollback occurs.

To return to direct mode, choose Direct to laptop while the Pi is reachable,
move its cable back to the laptop, renew laptop DHCP if needed, scan and confirm.
Saved Wi-Fi can provide a management path when Ethernet is disconnected.

## Location Wi-Fi

1. Initially use direct Ethernet and pair the Pi with the owning application.
2. Open Network setup, choose the location SSID and password, then Connect.
3. Join the laptop to the same reachable LAN. Remove direct Ethernet when ready
   to use only Wi-Fi, then Scan LAN or Probe IP on the Pi's Wi-Fi address.
4. The app verifies UUID/credential and asks the Pi to verify the owning backend
   before saving both addresses. Device ownership is not changed.

Previously saved Wi-Fi profiles can reconnect without re-entering the password.
The setup hotspot remains a recovery path if no saved connection is available;
this release does not add enterprise 802.1X or captive-portal onboarding.

## Reconnection and Limits

- Devices automatically rescans every 45 seconds while visible, with no active
  assessment, pairing or network dialog. Manual Scan LAN is always available.
- Direct gateways are probed first. Paired hostnames are also tried via `.local`
  resolution, followed by bounded `/24` scans near local IPv4 addresses.
- Known hostname discovery depends on mDNS support. Broad subnets/VLANs,
  blocked multicast or unknown unpaired devices may require Probe IP.
- Guest/client isolation, routed subnets and corporate ACLs can prevent camera
  traffic or callbacks even if internet access works. Use a reachable LAN and
  allow TCP 8765 to the Pi and TCP 8000 to the owning laptop.
- Scan does not reset pairing or start detection. Network changes are rejected
  during preparing/running/stopping assessments. A recording interrupted by
  disconnection is not silently resumed; start a new session after recovery.
- For a mobile multi-camera kit, a dedicated router plus enough LAN ports is
  convenient. Keep Pi Ethernet in Location mode; the router provides all leases.
- The backend selects its callback using the OS route to each Pi, not a guessed
  gateway address. UUID and device-token checks are required before updates.

No claim of successful physical router/cable-move testing should be inferred
from unit/browser tests alone. Consult the delivery verification document for
the checks actually performed on the connected devices.
