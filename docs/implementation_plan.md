# Implementation Plan

This document is the engineering gate plan. For product scope and feature priority, use:

- `docs/mvp_scope.md` for the MVP feature boundary.
- `docs/priority_roadmap.md` for implementation order.
- `docs/future_features.md` for planned post-MVP features.

## Current Product Direction

The immediate product direction is a stable offline-first single-camera MVP:

```text
Raspberry Pi Edge -> Local FastAPI Backend -> Local Database -> Electron Desktop
```

Cloud sync, multi-camera, fleet management, licensing, and enterprise deployment are valid future directions, but they should not block the first usable MVP.

The next engineering priorities are:

1. Live Assessment productization.
2. Worker identity and enrollment workflow.
3. Provisional RULA/REBA scoring workflow.
4. Event Engine.
5. Worker Timeline and Session Review.
6. Exposure Analytics.
7. MVP Reports.
8. Deployment hardening.

## Gate 0: Documentation and Inspection

Status: in progress.

Deliverables:

- `docs/architecture.md`
- `docs/database_design.md`
- `docs/api_contract.md`
- `docs/implementation_plan.md`

Completed findings:

- Local application repo is empty.
- Local Hailo repo currently contains only `PRD.md`.
- Legacy repo contains useful RULA/REBA scoring and session review concepts.
- Raspberry Pi has HailoRT 4.23, active HailoRT service, Hailo-8 detected, Hailo pose models installed, and Hailo Apps examples available.

Next approval point:

- Review and approve these documents before coding starts.

## Gate 1: Backend Foundation

Create FastAPI backend in `RULA-REBA_APP/backend`.

Tasks:

- Add Python project layout.
- Add FastAPI app factory.
- Add settings module using environment variables.
- Add SQLAlchemy 2.0 models.
- Add Alembic migrations.
- Add PostgreSQL connection configuration.
- Add health endpoints.
- Add test setup with pytest.

Acceptance criteria:

- `GET /health` returns backend status.
- `GET /api/v1/version` returns API version.
- Alembic can create all initial tables.
- Unit tests run locally.

## Gate 2: Database and Domain Services

Tasks:

- Implement worker registry service.
- Implement camera node registry service.
- Implement session manager.
- Implement detection ingestion persistence.
- Implement snapshot metadata persistence.
- Implement activity and review field models.

Acceptance criteria:

- A session can be created, started, stopped, reviewed, and completed through REST API.
- Detections can be inserted from validated schemas.
- Snapshot metadata can be associated with detections and sessions.

## Gate 3: RULA/REBA Scoring Service

Tasks:

- Extract scoring lookup tables from legacy reference.
- Convert legacy scoring into pure backend functions.
- Add typed input and output schemas.
- Add tests for low, medium, and high risk fixtures.
- Mark final scores as requiring manual review fields when load/coupling/activity are unknown.

Acceptance criteria:

- Scoring functions have deterministic unit tests.
- RULA and REBA return final score, risk level, and component breakdown.
- Review workflow can recalculate final score after manual input.

## Gate 4: WebSocket Hub

Tasks:

- Implement edge ingest WebSocket endpoint.
- Implement desktop live subscription WebSocket endpoint.
- Add heartbeat schema.
- Add detection event schema.
- Add backend-side event fanout per session.
- Add validation and error acknowledgements.

Acceptance criteria:

- Edge client can connect and send heartbeat.
- Edge client can stream detection events.
- Desktop client can subscribe to a session and receive live events.
- Invalid payloads are rejected with explicit error messages.

## Gate 5: Edge Node MVP

Target repo: `RULA-REBA_Detection_HailoAI`.

Tasks:

- Initialize proper edge project structure.
- Reuse or wrap Hailo Apps pose pipeline.
- Select `yolov8s_pose_h8.hef` or `yolov8s_pose_h8l_pi.hef` after benchmark.
- Implement ByteTrack integration.
- Implement soft Re-ID gallery with 10 second retention.
- Implement snapshot generation every 5 seconds and on significant posture/risk change.
- Implement WebSocket client.
- Implement local durable buffer for offline backend.
- Add systemd service file.

Acceptance criteria:

- Edge can run headless on Pi.
- Edge sends heartbeat.
- Edge sends detection payloads matching `api_contract.md`.
- Edge reconnects after backend restart.
- No Raspberry Pi files are overwritten without backup.

## Gate 6: Electron Desktop MVP

Tasks:

- Scaffold Electron + React + Vite + TypeScript.
- Add Material UI.
- Add app shell with pages:
  - Dashboard
  - Live Assessment
  - Session Review
  - History
  - Reports
  - Settings
- Implement API client.
- Implement WebSocket live view.
- Implement session start/stop.
- Implement review forms for identity, load, coupling, activity, and wrist twist.

Acceptance criteria:

- Operator can create a session.
- Operator can see live worker detections.
- Operator can stop session and complete review.
- Final assessments are saved through backend.

## Gate 7: Analytics and Reports

Tasks:

- Implement average RULA.
- Implement average REBA.
- Implement peak risk.
- Implement exposure duration.
- Implement daily, weekly, monthly trends.
- Implement high-risk worker ranking.
- Implement department comparison.
- Implement PDF report export.
- Implement Excel report export.

Acceptance criteria:

- Dashboard reads aggregate metrics from backend.
- PDF and Excel reports include worker, department, date, snapshots, RULA, REBA, and risk category.

## Gate 8: Integration and Deployment

Tasks:

- Create backend `.env.example`.
- Create Docker Compose for PostgreSQL and backend if appropriate.
- Add local dev scripts.
- Add Raspberry Pi deploy instructions.
- Add systemd install script for edge node.
- Add end-to-end smoke test procedure.

Acceptance criteria:

- Backend runs on master node.
- Desktop connects to backend.
- Edge Pi streams live data to backend.
- Session can be completed end to end.

## Engineering Risks

- Hailo Apps API may require adapting to its callback/pipeline structure instead of a simple frame loop.
- Python 3.13 on the Pi may limit third-party package availability.
- Hailo pose output format must be normalized to COCO-style keypoints before backend scoring.
- Single-camera posture cannot fully observe rotation, depth, load, or coupling; final score must include manual validation.
- Re-ID quality will depend on lighting, occlusion, and uniform similarity.

## Immediate Next Task After Approval

Start Gate 1 by scaffolding the FastAPI backend and initial database migration in `RULA-REBA_APP`.
