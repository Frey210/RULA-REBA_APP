# Database Design

## Database

Use PostgreSQL for Phase 1.

Reasons:

- Multi-camera roadmap.
- Concurrent backend and desktop access through APIs.
- Time-series style detection history.
- Reporting and analytics queries.
- Safer migration path than SQLite.

Use SQLAlchemy models and Alembic migrations. The backend is the only component allowed to write to PostgreSQL.

## Entity Overview

Required PRD entities:

- `workers`
- `sessions`
- `camera_nodes`
- `detections`
- `snapshots`
- `activities`
- `reports`

Additional support entities:

- `users`
- `refresh_tokens`
- `session_workers`
- `assessments`
- `review_items`
- `edge_events`
- `device_pairings`

## Tables

### `users`

Stores application users for JWT/Bearer authentication.

Columns:

- `id`: UUID primary key.
- `email`: text, required, unique.
- `password_hash`: text, required.
- `full_name`: text, nullable.
- `is_active`: boolean, default true.
- `is_superuser`: boolean, default false.
- `created_at`: timestamptz.
- `updated_at`: timestamptz.

Indexes:

- unique index on `email`.

### `refresh_tokens`

Stores revocable refresh tokens.

Columns:

- `id`: UUID primary key.
- `user_id`: UUID foreign key to `users.id`.
- `token_hash`: text, required, unique.
- `expires_at`: timestamptz, required.
- `revoked_at`: timestamptz, nullable.
- `created_at`: timestamptz.

Indexes:

- index on `user_id`.
- unique index on `token_hash`.

### `workers`

Stores known worker identities.

Columns:

- `id`: UUID primary key.
- `owner_user_id`: UUID foreign key to `users.id`.
- `employee_number`: text, nullable, unique.
- `name`: text, required.
- `department`: text, nullable.
- `position`: text, nullable.
- `is_active`: boolean, default true.
- `created_at`: timestamptz.
- `updated_at`: timestamptz.

Indexes:

- unique index on `employee_number` where not null.
- index on `department`.
- index on `owner_user_id`.

### `camera_nodes`

Stores edge node registrations.

Columns:

- `id`: UUID primary key.
- `owner_user_id`: UUID foreign key to `users.id`, nullable until paired.
- `cam_id`: text, required, unique. Example: `CAM_01`.
- `hostname`: text, nullable.
- `device_type`: text, nullable. Example: `raspberry_pi_5_hailo8`.
- `stream_uri`: text, nullable.
- `status`: text, required. Values: `offline`, `online`, `degraded`.
- `last_seen_at`: timestamptz, nullable.
- `metadata`: jsonb, default `{}`.
- `paired_at`: timestamptz, nullable.
- `created_at`: timestamptz.
- `updated_at`: timestamptz.

Indexes:

- unique index on `cam_id`.
- index on `status`.
- index on `last_seen_at`.
- index on `owner_user_id`.

### `device_pairings`

Stores local-network pairing state for Raspberry Pi edge nodes.

Columns:

- `id`: UUID primary key.
- `camera_node_id`: UUID foreign key to `camera_nodes.id`, nullable until registration completes.
- `owner_user_id`: UUID foreign key to `users.id`.
- `pairing_code_hash`: text, required.
- `status`: text, required. Values: `pending`, `paired`, `expired`, `revoked`.
- `expires_at`: timestamptz, required.
- `paired_at`: timestamptz, nullable.
- `created_at`: timestamptz.
- `updated_at`: timestamptz.

Indexes:

- index on `owner_user_id`.
- index on `camera_node_id`.
- index on `status`.

### `sessions`

Stores monitoring sessions.

Columns:

- `id`: UUID primary key.
- `owner_user_id`: UUID foreign key to `users.id`.
- `session_code`: text, required, unique. Example: `SESSION_20260623_001`.
- `status`: text, required. Values: `created`, `running`, `review_pending`, `completed`, `cancelled`.
- `started_at`: timestamptz, nullable.
- `stopped_at`: timestamptz, nullable.
- `completed_at`: timestamptz, nullable.
- `created_by`: text, nullable.
- `notes`: text, nullable.
- `metadata`: jsonb, default `{}`.
- `created_at`: timestamptz.
- `updated_at`: timestamptz.

Indexes:

- unique index on `session_code`.
- index on `status`.
- index on `started_at`.
- index on `owner_user_id`.

### `session_workers`

Maps temporary Re-ID identities to confirmed workers within a session.

Columns:

- `id`: UUID primary key.
- `session_id`: UUID foreign key to `sessions.id`.
- `worker_id`: UUID foreign key to `workers.id`, nullable until confirmed.
- `edge_worker_id`: text, required. Example: `WORKER_E47A`.
- `tracking_id`: integer, nullable.
- `identity_status`: text, required. Values: `unconfirmed`, `confirmed`, `new_worker`.
- `reid_confidence`: numeric, nullable.
- `confirmed_at`: timestamptz, nullable.
- `created_at`: timestamptz.
- `updated_at`: timestamptz.

Indexes:

- index on `session_id`.
- index on `worker_id`.
- unique index on `(session_id, edge_worker_id)`.

### `detections`

Stores normalized edge detections.

Columns:

- `id`: UUID primary key.
- `session_id`: UUID foreign key to `sessions.id`.
- `camera_node_id`: UUID foreign key to `camera_nodes.id`.
- `session_worker_id`: UUID foreign key to `session_workers.id`, nullable.
- `schema_version`: text, required.
- `frame_id`: bigint, required.
- `timestamp_ms`: bigint, required.
- `observed_at`: timestamptz, required.
- `edge_worker_id`: text, required.
- `tracking_id`: integer, required.
- `confidence`: numeric, nullable.
- `reid_confidence`: numeric, nullable.
- `bbox`: jsonb, required.
- `keypoints`: jsonb, required.
- `angles`: jsonb, nullable.
- `raw_payload`: jsonb, required.
- `created_at`: timestamptz.

Indexes:

- index on `session_id`.
- index on `camera_node_id`.
- index on `session_worker_id`.
- index on `(session_id, observed_at)`.
- index on `(session_id, edge_worker_id)`.

### `snapshots`

Stores snapshot metadata. Image files should be stored on disk or object storage; PostgreSQL stores paths and metadata.

Columns:

- `id`: UUID primary key.
- `session_id`: UUID foreign key to `sessions.id`.
- `detection_id`: UUID foreign key to `detections.id`, nullable.
- `camera_node_id`: UUID foreign key to `camera_nodes.id`.
- `session_worker_id`: UUID foreign key to `session_workers.id`, nullable.
- `snapshot_type`: text, required. Values: `interval`, `score_change`, `manual`, `event`.
- `file_path`: text, required.
- `thumbnail_path`: text, nullable.
- `captured_at`: timestamptz, required.
- `metadata`: jsonb, default `{}`.
- `created_at`: timestamptz.

Indexes:

- index on `session_id`.
- index on `session_worker_id`.
- index on `captured_at`.

### `activities`

Stores operator-confirmed activity labels and manual ergonomic inputs.

Columns:

- `id`: UUID primary key.
- `session_id`: UUID foreign key to `sessions.id`.
- `session_worker_id`: UUID foreign key to `session_workers.id`.
- `activity_type`: text, required. Example: `lifting`, `carrying`, `overhead_work`.
- `load_category`: text, nullable. Example: `<5kg`, `5_10kg`, `10_20kg`, `gt20kg`.
- `load_score`: integer, nullable.
- `coupling_score`: integer, nullable.
- `activity_score`: integer, nullable.
- `wrist_twist_score`: integer, nullable.
- `started_at`: timestamptz, nullable.
- `ended_at`: timestamptz, nullable.
- `confirmed_by`: text, nullable.
- `created_at`: timestamptz.
- `updated_at`: timestamptz.

Indexes:

- index on `session_id`.
- index on `session_worker_id`.
- index on `activity_type`.

### `assessments`

Stores final and provisional RULA/REBA results.

Columns:

- `id`: UUID primary key.
- `session_id`: UUID foreign key to `sessions.id`.
- `session_worker_id`: UUID foreign key to `session_workers.id`.
- `activity_id`: UUID foreign key to `activities.id`, nullable.
- `assessment_type`: text, required. Values: `rula`, `reba`.
- `assessment_status`: text, required. Values: `provisional`, `final`.
- `score`: integer, required.
- `risk_level`: text, required.
- `score_a`: integer, nullable.
- `score_b`: integer, nullable.
- `breakdown`: jsonb, required.
- `source_detection_ids`: jsonb, default `[]`.
- `calculated_at`: timestamptz, required.
- `created_at`: timestamptz.

Indexes:

- index on `session_id`.
- index on `session_worker_id`.
- index on `assessment_type`.
- index on `assessment_status`.
- index on `score`.

### `review_items`

Tracks outstanding review work after a session stops.

Columns:

- `id`: UUID primary key.
- `session_id`: UUID foreign key to `sessions.id`.
- `session_worker_id`: UUID foreign key to `session_workers.id`, nullable.
- `review_type`: text, required. Values: `identity`, `load`, `coupling`, `activity`, `wrist_twist`.
- `status`: text, required. Values: `pending`, `completed`, `skipped`.
- `payload`: jsonb, default `{}`.
- `resolved_payload`: jsonb, nullable.
- `resolved_at`: timestamptz, nullable.
- `created_at`: timestamptz.
- `updated_at`: timestamptz.

Indexes:

- index on `session_id`.
- index on `status`.
- index on `review_type`.

### `reports`

Stores generated report metadata.

Columns:

- `id`: UUID primary key.
- `owner_user_id`: UUID foreign key to `users.id`, nullable.
- `session_id`: UUID foreign key to `sessions.id`, nullable.
- `report_type`: text, required. Values: `pdf`, `excel`.
- `status`: text, required. Values: `queued`, `generated`, `failed`.
- `file_path`: text, nullable.
- `generated_by`: text, nullable.
- `generated_at`: timestamptz, nullable.
- `metadata`: jsonb, default `{}`.
- `created_at`: timestamptz.
- `updated_at`: timestamptz.

Indexes:

- index on `session_id`.
- index on `status`.
- index on `report_type`.
- index on `owner_user_id`.

### `edge_events`

Stores non-detection edge events for audit and debugging.

Columns:

- `id`: UUID primary key.
- `camera_node_id`: UUID foreign key to `camera_nodes.id`, nullable.
- `event_type`: text, required. Values: `heartbeat`, `connect`, `disconnect`, `buffer_flush`, `error`.
- `payload`: jsonb, required.
- `received_at`: timestamptz, required.
- `created_at`: timestamptz.

Indexes:

- index on `camera_node_id`.
- index on `event_type`.
- index on `received_at`.

## Migration Strategy

Initial Alembic migration:

1. Create all enum-like status columns as text with application-level validation first.
2. Add foreign keys and indexes.
3. Add JSONB columns for payload compatibility.
4. Add created/updated timestamps.

Later hardening:

- Add PostgreSQL enum types or check constraints after payloads stabilize.
- Add partitioning for `detections` if data volume grows.
- Add retention policy for raw detections and snapshots.

## Data Retention

Recommended defaults:

- Keep final assessments, workers, sessions, reports indefinitely.
- Keep raw detections for 90 days by default.
- Keep full snapshots for 180 days by default.
- Keep thumbnails indefinitely if report audit needs visual traceability.
