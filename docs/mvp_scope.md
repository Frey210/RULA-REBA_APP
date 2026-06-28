# MVP Scope

Dokumen ini mendefinisikan ruang lingkup produk MVP awal ErgoQuipt. Fokus MVP adalah membuat satu alur assessment ergonomi yang dapat dipakai end-to-end dengan satu Raspberry Pi edge device, satu kamera, backend lokal, dan aplikasi Electron.

## Prinsip MVP

- Single camera harus matang sebelum multi-camera.
- Sistem harus berjalan offline di jaringan lokal.
- Backend lokal menjadi single source of truth.
- Electron berperan sebagai operator UI, bukan tempat logika bisnis utama.
- Data live stream harus diubah menjadi event, timeline, exposure, dan report yang bisa dipakai untuk keputusan HSE.
- RULA/REBA dari AI diposisikan sebagai screening/provisional score sampai operator mengonfirmasi input manual yang tidak terlihat kamera.

## Target Pengguna MVP

- HSE officer yang melakukan assessment ergonomi di area kerja.
- Supervisor produksi yang ingin melihat ringkasan risiko worker.
- Admin/operator yang melakukan pairing Raspberry Pi dan menjalankan sesi assessment.

## Arsitektur MVP

```text
Raspberry Pi Edge
  - Camera capture
  - Hailo pose detection
  - Tracking and soft Re-ID
  - Overlay stream
  - WebSocket event sender

Local Backend
  - FastAPI
  - JWT authentication
  - Device pairing
  - Session manager
  - Worker registry
  - Detection ingestion
  - Event engine
  - Exposure analytics
  - Report metadata

Electron Desktop
  - Login
  - Device management
  - Live assessment
  - Session review
  - Worker registry
  - History and analytics
  - Reports
```

## MVP Must-Have Features

### 1. Authentication and Data Ownership

Status: implemented foundation, continue hardening.

Requirements:

- User login with JWT/Bearer token.
- All workers, sessions, devices, reports, and analytics scoped to the authenticated user.
- Desktop must not access the database directly.
- Backend API remains the only data access layer.

Acceptance criteria:

- User can log in from Electron.
- User only sees their own workers, devices, and sessions.
- API rejects unauthenticated requests.

### 2. Device Discovery and Pairing

Status: implemented foundation, continue UX hardening.

Requirements:

- Electron can discover Raspberry Pi edge device on the local network.
- User can pair a discovered edge device.
- User can rename device with a custom display name.
- User can delete/revoke a paired device.
- Raspberry Pi stays idle until a paired, authenticated session is started.

Acceptance criteria:

- A paired device appears in device management.
- Deleted device cannot stream into the backend.
- Heavy Hailo detection starts only during an active session.

### 3. Live Assessment Single Camera

Status: active priority.

Requirements:

- Operator can start and stop a session.
- Live camera stream is visible with optional overlay.
- Overlay shows person bounding boxes, skeleton, worker identity, and basic risk signal.
- UI supports multiple detected workers in the same frame.
- Worker cards stay stable during brief detection gaps.
- Stream does not become heavier over time.

Acceptance criteria:

- Session can run for at least 30 minutes without visible UI degradation.
- Re-ID identity remains stable through brief misses.
- Overlay aligns with the live camera frame.
- UI shows each active worker as a separate readable card.

### 4. Worker Registry and Enrollment Photos

Status: implemented storage/display foundation.

Requirements:

- User can create and edit worker profiles.
- User can upload full-body enrollment photos for front, left, and right views.
- Photos are private to the authenticated user.
- Photos are used first for visual reference, then later for candidate identity matching.

Acceptance criteria:

- Worker photos can be uploaded, replaced, displayed, and deleted.
- Worker assignment during a session can persist to the session record.
- Enrollment feature does not block the live assessment workflow.

### 5. Provisional RULA/REBA Scoring

Status: priority after live assessment stability.

Requirements:

- Backend calculates provisional RULA/REBA from normalized pose angles where observable.
- Scores expose component breakdown, confidence, and missing manual inputs.
- Manual review can update load, coupling, activity, wrist twist, and other non-observable fields.

Acceptance criteria:

- Provisional score is visible during live assessment.
- Final score can be recalculated after review.
- UI clearly distinguishes provisional AI score from reviewed final score.

### 6. Event Engine

Status: implemented for worker presence, high-risk transitions, release hysteresis, sustained high-risk posture, score statistics, and session summaries.

Requirements:

- Convert frame-level detections into useful ergonomic events.
- Detect high-risk start/end, sustained posture, peak score, worker presence, and identity changes.
- Store event duration, worker identity, score/risk level, camera, session, and reference detection/snapshot.

Example events:

- `high_risk_started`
- `high_risk_ended`
- `sustained_neck_flexion`
- `worker_entered`
- `worker_left`
- `identity_changed`
- `snapshot_captured`

Acceptance criteria:

- Database does not rely on raw frame stream for all analytics.
- Session review can show event summaries.
- Analytics can calculate exposure from events.

### 7. Worker Timeline and Session Review

Status: implemented baseline with event navigation, filters, risk sorting, snapshots, identity confirmation, manual scoring, and review completion.

Requirements:

- Session review shows timeline of ergonomic events.
- User can filter by worker, risk level, and event type.
- User can inspect representative snapshots or event clips.
- User can confirm identity and manual scoring fields from review screen.

Acceptance criteria:

- Operator can understand what happened in a session without reading raw JSON.
- Review workflow produces final assessments.
- Important events have enough context for audit.

### 8. Exposure Analytics

Status: after Event Engine and Timeline.

Requirements:

- Calculate total high-risk duration per worker.
- Calculate average and peak RULA/REBA per worker/session/day.
- Show top risky workers and sessions.
- Show trend charts for daily/weekly review.

Acceptance criteria:

- Dashboard answers "who is most exposed" and "where should we intervene first".
- Analytics are generated from stored event/session data.

### 9. Lightweight Recording and Snapshot Review

Status: after Event Engine.

Requirements:

- Capture snapshots on interval and important event changes.
- Optional short event clips can be added after snapshot flow is stable.
- Store files on disk/object storage; database stores metadata and paths.

Acceptance criteria:

- Review can show visual evidence for high-risk events.
- Storage usage remains predictable.
- Recording can be disabled from settings.

### 10. MVP Reports

Status: after analytics.

Requirements:

- Generate session report with worker list, score summaries, event timeline, exposure duration, snapshots, and review notes.
- Export to PDF first; Excel/CSV can follow.

Acceptance criteria:

- HSE user can produce a report from a completed session.
- Report includes enough data for internal ergonomic review.

## Explicitly Out of MVP

- Cloud sync.
- Multi-site management.
- Licensing system.
- Fleet management for many edge devices.
- Mobile app.
- Web dashboard for managers.
- Enterprise SSO/LDAP.
- Full 3D reconstruction.
- Continuous full-session video recording.
- Automatic ergonomic recommendation engine beyond simple risk summary.
- Production installer with embedded PostgreSQL and Windows Service hardening.

These are valid product directions, but they should not block the first usable MVP.
