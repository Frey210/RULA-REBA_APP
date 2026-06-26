# Future Features

Dokumen ini mencatat fitur yang penting untuk arah produk jangka panjang, tetapi tidak termasuk scope MVP awal. Fitur di sini boleh memengaruhi desain arsitektur, namun tidak boleh menghambat penyelesaian single-camera MVP.

## Cloud Sync

Target:

- Local backend remains the operational source of truth.
- Cloud receives synchronized data for backup, multi-device access, and cross-site analytics.
- Sync is handled by backend service, not directly by Electron.

Planned capabilities:

- Background upload of sessions, workers, assessments, events, reports, and selected media.
- Retry queue when internet is unavailable.
- Conflict handling for edited records.
- Cloud object storage for report, snapshot, and clip files.

Not for MVP because:

- Offline local workflow must be reliable first.
- Event and report data model needs to stabilize before sync.

## Multi-User Organization Model

Target:

- Multiple users under one organization.
- Role-based access control.
- Shared worker registry and device pool.

Planned roles:

- Operator
- HSE reviewer
- Supervisor/manager
- Admin

Not for MVP because:

- Current simple user ownership is enough for early validation.
- Role complexity should wait until workflows are proven.

## Multi-Camera and Multi-Edge Support

Target:

- Multiple Raspberry Pi edge devices per site.
- Concurrent live assessment from multiple cameras.
- Cross-camera worker identity support where feasible.

Planned capabilities:

- Device grouping by area/line/station.
- Per-camera health and stream status.
- Session with one or more cameras.
- Camera-specific calibration and thresholds.

Not for MVP because:

- Single-camera scoring, UI, and review must be stable first.
- Multi-camera increases identity, bandwidth, and storage complexity.

## Fleet Management

Target:

- Central management for edge device health and configuration.

Planned capabilities:

- Firmware/software version inventory.
- Hailo status, CPU, RAM, temperature, FPS, latency.
- Remote restart/reconfigure.
- Model distribution.
- Device logs and diagnostics.

Not for MVP because:

- Local device management and pairing already cover early deployment needs.

## Advanced Device Configuration Center

Target:

- Backend-managed configuration for edge runtime behavior.

Planned settings:

- Camera resolution.
- Stream FPS.
- Detection FPS.
- Confidence thresholds.
- Overlay options.
- Snapshot interval.
- Recording mode.
- Re-ID thresholds.
- Calibration profile.

MVP subset:

- Store basic device/session settings locally.
- Keep advanced remote configuration for later.

## Recording Engine

Target:

- Reviewable video evidence for ergonomic events.

Planned capabilities:

- Event-based video clips.
- Configurable pre-roll and post-roll.
- Retention policy.
- Local/object storage integration.
- Clip playback from session review.

MVP subset:

- Snapshots and optional short clips only after event engine is stable.
- Avoid continuous full-session recording at MVP because it increases storage and performance risk.

## Installer and Windows Service Productization

Target:

- One installer for non-technical users.
- Backend runs as Windows Service.
- Electron is only the desktop UI.
- Database, logs, storage, migrations, and firewall rules are configured automatically.

Planned installation layout:

```text
C:\Program Files\ErgoQuipt
  Backend
  Desktop
  Config
  Logs
  Storage
  Models
  Database
  Update
```

Not for MVP because:

- Core workflows should stabilize first.
- Packaging too early can slow iteration.

## Cloud Platform and Licensing

Target:

- Commercial SaaS/enterprise layer.

Planned capabilities:

- License activation.
- Organization management.
- Subscription plan limits.
- Cross-site dashboard.
- Backup and restore.
- Notification service.
- API integration.

Not for MVP because:

- It depends on stable local product value.

## Advanced Re-ID

Target:

- More stable identity matching using enrollment photos and appearance embeddings.

Planned capabilities:

- Body appearance embedding model.
- Enrollment image quality score.
- Candidate ranking against worker registry.
- Manual confirmation loop.
- Optional face-blurred privacy-preserving enrollment.

MVP subset:

- Manual assignment plus full-body enrollment photo storage.
- Lightweight candidate assistance can be introduced only after quality and privacy constraints are clear.

## 3D Pose and Digital Human View

Target:

- 3D representation of worker posture for improved interpretability.

Planned capabilities:

- 3D skeleton visualization.
- Calibration-aware pose normalization.
- Optional avatar view for review.

Not for MVP because:

- Single-camera 2D pose is already enough for early ergonomic screening.
- 3D accuracy requires calibration and validation work.

## Mobile and Web Dashboard

Target:

- Manager/supervisor access from browser or mobile.

Planned capabilities:

- Read-only analytics dashboard.
- Report viewing.
- Notifications.
- Cross-site summaries.

Not for MVP because:

- Electron desktop is the primary operator tool.
- Cloud sync and organization model should exist first.

