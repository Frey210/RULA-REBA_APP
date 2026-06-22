# ErgoQuipt Ergonomic Assessment Platform Architecture

## Scope

This document defines the Phase 1 architecture for the ErgoQuipt RULA/REBA platform.
It follows `D:\Aerasea\RULA-REBA_Detection_HailoAI\PRD.md` and the attached project rules.

Phase 1 target:

- One Raspberry Pi 5 edge node with Hailo-8 and one USB camera.
- One FastAPI backend with PostgreSQL.
- One Electron + React + TypeScript desktop application.
- Architecture prepared for multiple camera nodes in Phase 2.

The edge repository must not calculate RULA or REBA. It only sends pose, identity, tracking, and snapshot metadata.

## Repository Roles

### `D:\Aerasea\RULA-REBA_APP`

Primary application repository. It will contain:

- FastAPI backend.
- SQLAlchemy models and Alembic migrations.
- WebSocket hub.
- Analytics engine.
- Report generation.
- Electron desktop application.

Current state: empty workspace before this documentation pass.

### `D:\Aerasea\RULA-REBA_Detection_HailoAI`

Edge detection system for Raspberry Pi 5 + Hailo-8.

Current local state: contains only `PRD.md`; it is not currently a git repository in the local workspace.

Target responsibilities:

- Camera capture.
- Hailo YOLO pose inference.
- ByteTrack tracking.
- Soft Re-ID.
- Snapshot generation.
- WebSocket client with buffering and heartbeat.

### `D:\Aerasea\RULA-REBA_Detection-main`

Legacy reference repository only.

Reusable concepts:

- RULA and REBA lookup tables.
- Angle-to-score workflow.
- Review workflow.
- Session and snapshot export concepts.

Do not copy the UI or pipeline blindly. The legacy app is a Windows CustomTkinter prototype that mixes UI, inference, scoring, history, and export.

## Raspberry Pi Audit Findings

Read-only inspection was performed against:

- Host: `ergoquipt-rr`
- SSH: `admin@192.168.137.199`

Observed environment:

- OS: Debian GNU/Linux 13 Trixie, version 13.5.
- Kernel: `6.12.75+rpt-rpi-2712`.
- Python: 3.13.5.
- HailoRT CLI: 4.23.0.
- Hailo firmware: 4.23.0.
- Device: Hailo-8 on PCIe, device id `0001:04:00.0`.
- `hailort.service`: loaded and active.
- Video devices are present at `/dev/video0`, `/dev/video1`, and Raspberry Pi media devices.

Available relevant models and assets:

- `/usr/share/hailo-models/yolov8s_pose_h8.hef`
- `/usr/share/hailo-models/yolov8s_pose_h8l_pi.hef`
- `/usr/share/hailo-models/yolov8s_pose_h10.hef`
- `/usr/share/rpi-camera-assets/hailo_yolov8_pose.json`
- `/usr/share/rpi-camera-assets/hailo_pose_inf_fl.json`
- Hailo Apps pose examples under `/home/admin/hailo-apps/hailo_apps/python/pipeline_apps/pose_estimation`
- Hailo Apps Re-ID examples under `/home/admin/hailo-apps/hailo_apps/python/pipeline_apps/reid_multisource`

Python package findings inside `/home/admin/hailo-apps/venv_hailo_apps`:

- `hailo_platform`: present.
- `gi`: present.
- `cv2`: present.
- `numpy`: present.
- `lap`: present.
- `cython_bbox`: present.
- `websockets`: missing.
- `fastapi`: missing.

Decision: use the existing Hailo Apps environment for inference compatibility, but isolate project-specific WebSocket/client dependencies in a project venv or install minimal additional packages only after backing up any modified files.

## System Architecture

```text
USB Camera
  |
  v
Raspberry Pi Edge Node
  - Hailo YOLOv8 pose inference
  - ByteTrack tracking
  - Soft Re-ID
  - Snapshot writer
  - Durable event buffer
  - WebSocket client
  |
  v
FastAPI Backend
  - WebSocket ingest
  - REST API
  - JWT/Bearer authentication
  - Device discovery and pairing broker
  - Session manager
  - Worker registry
  - RULA/REBA scoring service
  - Analytics service
  - Report service
  |
  v
PostgreSQL
  - workers
  - sessions
  - camera_nodes
  - detections
  - snapshots
  - activities
  - reports
  |
  v
Electron Desktop App
  - dashboard
  - live assessment
  - session review
  - history
  - reports
  - settings
```

## Runtime Responsibilities

### Edge Node

The edge node sends versioned data packets:

- heartbeat events.
- detection frames.
- worker track metadata.
- keypoints.
- bounding boxes.
- snapshot paths or uploaded snapshot references.

It does not persist authoritative session history and does not compute RULA/REBA.

### Backend

The backend is the system of record.

Responsibilities:

- Register camera nodes.
- Create and stop sessions.
- Receive live edge data over WebSocket.
- Persist raw pose and snapshot metadata.
- Calculate provisional RULA/REBA from pose data where useful.
- Store manual review decisions.
- Generate final RULA/REBA after identity, load, coupling, and activity validation.
- Serve analytics and reports.

### Desktop App

The Electron app is the operator workstation.

Responsibilities:

- Start and stop sessions.
- Show live detections and provisional risk.
- Review snapshots after session stop.
- Confirm worker identity.
- Confirm load, coupling, activity, and wrist twist fields where required.
- Save final assessments.
- Display history, analytics, and reports.

## Edge Pipeline Decision

Use Hailo YOLOv8 pose as the primary pose source.

Reasoning:

- The Pi already has HailoRT 4.23 and Hailo-8 working.
- Hailo pose HEF files are already installed.
- Hailo Apps contains pose estimation examples compatible with the environment.
- Avoiding MediaPipe matches the PRD and reduces CPU load.

Tracking decision:

- Start with ByteTrack.
- `lap` and `cython_bbox` are already installed in the Hailo venv.
- ByteTrack is enough for the Phase 1 goal of 2-3 workers and single-camera continuity.
- BoT-SORT can be evaluated later if appearance-based matching is needed beyond the 10 second soft Re-ID target.

Re-ID decision:

- Implement Phase 1 soft Re-ID.
- Generate a lightweight appearance descriptor from person crops using HSV/color histogram plus optional Hailo/person embedding if a compatible model is validated.
- Maintain a short-lived lost-track gallery for 10 seconds.
- Match by descriptor similarity and spatial/temporal constraints.
- Emit `worker_id`, `tracking_id`, and `reid_confidence` in every detection payload.

## Legacy Logic Extraction

The legacy repository has usable scoring functions in `src/ergotracker/core/scoring.py`.

Extract:

- REBA lookup tables.
- RULA lookup tables.
- Risk category mapping.
- Manual load/coupling/activity adjustment concepts.

Rework required:

- Put scoring into pure backend functions with unit tests.
- Validate table values against official worksheet examples.
- Treat single-camera angles as screening estimates.
- Keep manual review fields mandatory for final score where AI cannot observe the variable directly.

## Session Workflow

1. Desktop starts a session through REST API.
2. Backend creates a session and marks the expected camera nodes.
3. Edge streams detections via WebSocket and includes session id once assigned.
4. Backend records detections and snapshots.
5. Desktop subscribes to live session updates.
6. User stops monitoring.
7. Backend marks session as `review_pending`.
8. Desktop opens session review:
   - choose snapshots,
   - confirm worker identity,
   - confirm load score,
   - confirm coupling score for REBA,
   - confirm activity score,
   - confirm wrist twist where needed for RULA.
9. Backend calculates final assessments.
10. Session becomes `completed`.

## Operational Requirements

Edge node:

- Runs headless.
- Starts on boot with `systemd`.
- Reconnects WebSocket automatically.
- Buffers events locally if backend is down.
- Sends heartbeat packets.
- Uses file backups before any modification on the Pi.

Backend:

- Database migrations through Alembic.
- OpenAPI documentation enabled.
- WebSocket payloads validated with Pydantic schemas.
- JWT/Bearer authentication for desktop users.
- User-scoped data access so workers, sessions, reports, and analytics are only visible to authorized users.
- Device pairing records so a Raspberry Pi edge node can only stream into an authorized installation/session.

Desktop:

- Electron + React + TypeScript + Material UI.
- No direct database access.
- All data access through backend API.

## Authentication and Data Ownership

Phase 1 will include simple JWT/Bearer authentication.

User flow:

1. User logs in from Electron with username/email and password.
2. Backend returns an access token and refresh token.
3. Electron stores tokens in secure local storage through the Electron main process.
4. REST calls use `Authorization: Bearer <token>`.
5. WebSocket connections provide the token during connection setup.

Data ownership:

- Sessions, workers, reports, and analytics are scoped to the authenticated user or organization.
- Camera nodes are paired to a user/organization before they can stream production detections.
- Admin-style multi-user roles can be added later without changing the core API shape.

## Raspberry Pi Discovery and Pairing

The Raspberry Pi must not run the heavy detection pipeline continuously.

Target behavior:

1. On boot, the Raspberry Pi starts a lightweight edge agent only.
2. The lightweight agent advertises itself on the local network with mDNS/ZeroConf and exposes a small pairing API.
3. Electron auto-searches the local network for compatible edge devices.
4. User selects a discovered Raspberry Pi and starts pairing.
5. Backend creates a short-lived pairing token.
6. Electron sends the token to the Raspberry Pi pairing endpoint.
7. The Raspberry Pi registers with the backend and remains idle.
8. The heavy Hailo pose pipeline starts only when an authenticated user starts a monitoring session for that paired camera.
9. When the session stops, the edge node stops inference and returns to idle mode.

Discovery options:

- Preferred: mDNS/ZeroConf service such as `_ergoquipt-edge._tcp.local`.
- Fallback: LAN subnet scan from Electron against a lightweight `/pairing/info` endpoint.

Pairing security:

- Pairing tokens are short-lived.
- Paired edge nodes store only a node credential, not a user password.
- Backend can revoke paired devices.
- The edge node refuses detection start commands unless paired and authorized by the backend.
