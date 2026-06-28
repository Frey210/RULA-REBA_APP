# Priority Roadmap

Dokumen ini menjadi urutan kerja utama setelah fondasi backend, Electron, dan edge device sudah berjalan. Roadmap ini sengaja memprioritaskan single-camera workflow yang stabil sebelum memperluas sistem ke cloud, multi-camera, atau enterprise features.

## Priority 0 - Stabilization Baseline

Goal: memastikan fitur yang sudah ada tidak mudah rusak saat fitur baru ditambahkan.

Work items:

- Keep backend tests, desktop lint/build, and Alembic migration checks passing.
- Keep Electron startup behavior clear when backend or Vite port is already occupied.
- Keep Raspberry Pi edge service boot-safe after shutdown/reboot.
- Maintain clear API contracts between edge, backend, and desktop.

Exit criteria:

- Developer can run backend and Electron reliably.
- Raspberry Pi can reboot without losing Hailo/boot configuration.
- Existing live session flow remains usable.

## Priority 1 - Live Assessment Productization

Goal: membuat layar live assessment terasa seperti produk, bukan debug console.

Work items:

- Improve multi-worker live layout.
- Ensure overlay aligns with camera stream.
- Keep live stream stable over long sessions.
- Preserve worker identity cards through short detection gaps.
- Add clear session state: idle, preparing, running, stopping, review pending.
- Add operator actions: start session, stop session, assign worker, open review.

Exit criteria:

- One session can be run end-to-end from Electron.
- UI remains readable with 2-3 workers.
- Operator does not need to inspect raw payloads.

## Priority 2 - Worker Identity and Enrollment

Goal: mengurangi kebingungan identitas worker saat live assessment.

Work items:

- Use worker registry as the authoritative identity list.
- Keep manual worker assignment persistent per session.
- Store front/left/right full-body enrollment photos.
- Add enrollment quality feedback for resolution, blur, and body framing.
- Prepare enrollment photos for future body appearance matching.

Exit criteria:

- Operator can assign Re-ID track to a registered worker.
- Assignment remains stable in session history.
- Enrollment photos are available during review and identity confirmation.

## Priority 3 - RULA/REBA Scoring Workflow

Goal: menghasilkan skor ergonomi yang bisa diaudit, bukan hanya angka sementara.

Work items:

- Normalize pose angles used by RULA/REBA.
- Calculate provisional RULA and REBA from observable posture.
- Mark missing manual inputs explicitly.
- Add manual review fields for load, coupling, activity, wrist twist, and other non-observable scoring inputs.
- Store provisional and final assessment separately.

Exit criteria:

- Live screen can show provisional risk.
- Review screen can produce final score.
- Stored score has component breakdown and source evidence.

## Priority 4 - Event Engine

Goal: mengubah stream frame menjadi kejadian ergonomi yang berguna.

Work items:

- Define event table/model and schemas.
- Detect risk transitions such as high-risk started/ended.
- Track event duration per worker and session.
- Attach representative detection and snapshot references.
- Create event summaries for session review.

Exit criteria:

- Analytics no longer depend on reading every raw detection frame.
- Session review can show timeline of important events.
- High-risk duration can be calculated reliably.

## Priority 5 - Session Review and Worker Timeline

Goal: membuat pengguna dapat memahami sesi setelah monitoring selesai.

Work items:

- Build review page based on event timeline.
- Filter timeline by worker, risk level, and event type.
- Show snapshots or representative frames for important events.
- Allow review completion and final assessment confirmation.

Exit criteria:

- A stopped session can be reviewed and completed.
- User can identify worst postures and confirm scoring inputs.

## Priority 6 - Exposure Analytics

Status: baseline implemented with period overview, worker/session ranking, daily trends, worst events, and average/peak RULA-REBA.

Goal: menghasilkan insight yang bernilai untuk HSE dan supervisor.

Work items:

- High-risk duration per worker.
- Average and peak RULA/REBA.
- Worst posture/event list.
- Top risky workers and sessions.
- Daily/weekly trend summaries.

Exit criteria:

- Dashboard answers where risk is concentrated.
- Analytics use persisted sessions, events, and assessments.

## Priority 7 - Reports

Status: baseline implemented with session PDF generation, authenticated report list, and download from Electron.

Goal: membuat output yang bisa dibagikan untuk audit internal.

Work items:

- Session report PDF.
- Worker exposure summary.
- Event timeline summary.
- Snapshot evidence.
- Review notes and final score breakdown.

Exit criteria:

- Completed session can produce a PDF report.
- Report can be used without opening the application.

## Priority 8 - Deployment Hardening

Goal: membuat aplikasi mudah dipakai tanpa terminal.

Work items:

- Package backend as a local service.
- Keep Electron as UI client.
- Add local storage/log folder conventions.
- Add automatic migration at service startup.
- Prepare installer strategy.

Exit criteria:

- User does not need to run `npm`, `python`, or `uvicorn` manually for normal use.
- Application can start after Windows reboot.
