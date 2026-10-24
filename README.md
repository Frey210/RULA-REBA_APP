# ERGoSIGHT

AI-Based Ergonomic Monitoring System for RULA/REBA assessment.

This repository contains the Electron desktop application, bundled FastAPI backend,
local SQLite storage, and review/reporting services for RULA/REBA assessment.

## Product Documentation

- [Panduan Pengguna MVP](output/pdf/ERGoSIGHT-Panduan-Pengguna-MVP.pdf)
- [Dokumen Teknis MVP](output/pdf/ERGoSIGHT-Dokumen-Teknis-MVP.pdf)

Rebuild both PDFs with `py -3.12 scripts\generate_product_docs.py`.

## Current Status

Version 0.2.2 includes authenticated pairing, multi-camera live workspace, scoped
worker assignment, provisional scoring, evidence-backed manual review, complete
PDF/Excel/ZIP documentation and private diagnostic export. Physical multi-Pi, 60-minute
load and reference ergonomic accuracy tests are still release gates. See
[stabilization delivery](docs/stabilization_delivery_2026-10-24.md).

## Backend Development

Use Python 3.12 explicitly because the Windows `python` command on this machine points to Python 2.7.

```powershell
cd D:\Aerasea\RULA-REBA_APP\backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

For local SQLite migration smoke tests:

```powershell
$env:DATABASE_URL='sqlite:///./migration_smoke.sqlite3'
.\.venv\Scripts\python.exe -m alembic upgrade head
```

## Electron Development

The Electron command starts FastAPI, Vite, and Electron together:

```powershell
cd D:\Aerasea\RULA-REBA_APP\desktop
npm.cmd run electron
```

It uses `backend\.venv` and the local SQLite database `backend\dev_server.sqlite3`.
Set `ERGOQUIPT_DATABASE_URL` before launching only when a different database is required.
Pending Alembic migrations are applied automatically before FastAPI starts.

To test source with the accounts, media and camera pairing already used by the
installed application, close the installed app/other backend first, then run:

```powershell
npm.cmd run electron:installed-profile
```

This explicitly reuses `%APPDATA%\ergosight-desktop` without changing its secret
or resetting device ownership. The launcher rejects a different backend version
or profile on port 8000. Default `npm.cmd run electron` remains a separate
development profile; do not pair an owned camera into an empty development DB.

## Windows installer

Build the complete Windows installer from the `desktop` directory:

```powershell
npm.cmd run dist:win
```

The default output is `desktop\installer\ERGoSIGHT-Setup-0.2.2.exe`. The current
delivery build is under `desktop\installer\reports-0.2.2\`. It bundles
Electron and FastAPI, applies migrations, creates shortcuts and a private-network
firewall rule. Normal installations require neither Python nor Node.js. Installer
execution/upgrade on a clean second laptop remains to be verified.

Production data, enrollment images, logs, and the generated JWT secret are stored
under `%APPDATA%\ergosight-desktop`. Uninstalling/upgrading preserves this directory.

## Session Documentation

Stop a session, finish its review as appropriate, then open Reports and select
Generate Report. PDF contains all observation/risk events, provisional and reviewed
assessments, manual inputs/component breakdowns, measurements, worker/camera scope,
and documentation photos. Version 0.2.2 separates the summary, each event/review,
photo pages and technical reference appendix with fixed leading and wrapping.
Missing or unverified information remains explicitly
marked. ZIP + Photos includes the same PDF, original available photos, CSV samples,
and a checksum/provenance manifest. Registry reference photos are labelled as
identity references, not posture evidence. Older reports are never overwritten.

Reports contain personal data. Downloads require the owning account; share exported
files only with authorized recipients. Download PDF, Download Excel and Download
ZIP are shown directly below Generate Report and on each report row. Older reports
without a format keep that button disabled; generate a new report for the session
to enable it. Excel includes filterable worker/event/review tables, representative
source measurements, review details, embedded photos and technical references.
All raw samples remain in the ZIP CSV. Excel is not required to generate files.
See [report export delivery](docs/report_exports_2026-10-24.md).

Devices > Diagnostics exports a separate
support ZIP without credentials, account details, raw logs, or photos. Automatic
raw-data deletion is disabled; use History to explicitly delete an unwanted stopped
session after exporting its documentation if needed.

## Connecting an edge device

- Direct LAN: connect the Raspberry Pi and laptop with an Ethernet cable, leave the laptop adapter on automatic DHCP, then open **Devices** and select **Scan LAN**. The edge address is `10.55.0.1`; Windows Internet Connection Sharing is not required.
- Wi-Fi onboarding: connect the laptop once to `ERGoSIGHT-CAM01` using the password on the device label, open **Devices**, pair the discovered edge, then select **Set up Wi-Fi**. Choose the destination network, enter its password, reconnect the laptop to that network, and run **Scan LAN** again.

If a development laptop previously used Windows Internet Connection Sharing, disable sharing and restore the Ethernet adapter to automatic DHCP before testing direct LAN.

Worker enrollment photos are stored privately under `backend\media\worker-enrollments`.
The frontend retrieves them through authenticated API requests; the media directory
is intentionally excluded from Git.
