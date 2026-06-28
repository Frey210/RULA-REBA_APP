# API Contract

## Versioning

All REST endpoints are under:

```text
/api/v1
```

All edge and desktop WebSocket messages include:

```json
{
  "schema_version": "1.0",
  "event_type": "..."
}
```

Breaking schema changes require a new major schema version.

## Edge Detection Payload

The edge node sends one detection event per frame or micro-batch.

Endpoint:

```text
WS /ws/v1/edge/{cam_id}
```

Message:

```json
{
  "schema_version": "1.0",
  "event_type": "detection",
  "cam_id": "CAM_01",
  "session_id": "SESSION_20260623_001",
  "timestamp": 1718742953123,
  "frame_id": 12345,
  "detections": [
    {
      "worker_id": "WORKER_E47A",
      "tracking_id": 4,
      "confidence": 0.92,
      "reid_confidence": 0.88,
      "bbox": [120.5, 80.0, 420.0, 720.0],
      "keypoints": {
        "format": "coco17",
        "points": [
          {"id": 0, "name": "nose", "x": 231.0, "y": 96.0, "score": 0.86},
          {"id": 5, "name": "left_shoulder", "x": 184.0, "y": 201.0, "score": 0.91}
        ]
      },
      "snapshot_path": "/var/lib/ergoquipt-edge/snapshots/CAM_01/20260623/12345.jpg",
      "metadata": {
        "model": "yolov8s_pose_h8",
        "tracker": "bytetrack"
      }
    }
  ]
}
```

Backend acknowledgement:

```json
{
  "schema_version": "1.0",
  "event_type": "ack",
  "message_id": "optional-client-message-id",
  "status": "accepted"
}
```

Validation error:

```json
{
  "schema_version": "1.0",
  "event_type": "error",
  "code": "VALIDATION_ERROR",
  "detail": "detections.0.keypoints.points is required"
}
```

## Edge Heartbeat Payload

```json
{
  "schema_version": "1.0",
  "event_type": "heartbeat",
  "cam_id": "CAM_01",
  "timestamp": 1718742953123,
  "status": "online",
  "metrics": {
    "fps": 25.4,
    "buffered_events": 0,
    "cpu_percent": 43.1,
    "memory_percent": 31.5,
    "hailo_device": "0001:04:00.0"
  }
}
```

## Desktop Live Subscription

Endpoint:

```text
WS /ws/v1/sessions/{session_id}/live
```

Backend live event:

```json
{
  "schema_version": "1.0",
  "event_type": "session_detection",
  "session_id": "SESSION_20260623_001",
  "cam_id": "CAM_01",
  "timestamp": 1718742953123,
  "detections": [
    {
      "worker_id": "WORKER_E47A",
      "tracking_id": 4,
      "confidence": 0.92,
      "reid_confidence": 0.88,
      "bbox": [120.5, 80.0, 420.0, 720.0],
      "keypoints": {
        "format": "coco17",
        "points": []
      },
      "provisional_scores": {
        "rula": {
          "score": 5,
          "risk_level": "Investigate Soon"
        },
        "reba": {
          "score": 7,
          "risk_level": "Medium"
        }
      }
    }
  ]
}
```

## REST Endpoints

Authenticated endpoints require:

```text
Authorization: Bearer <access_token>
```

### Health

```text
GET /health
```

Response:

```json
{
  "status": "ok"
}
```

### Version

```text
GET /api/v1/version
```

Response:

```json
{
  "api_version": "1.0",
  "app": "ergoquipt"
}
```

## Workers

## Auth

### Register user

```text
POST /api/v1/auth/register
```

Request:

```json
{
  "email": "operator@example.com",
  "username": "operator",
  "password": "change-me",
  "full_name": "HSE Operator"
}
```

### Login

```text
POST /api/v1/auth/login
```

Request:

```json
{
  "email": "operator@example.com",
  "password": "change-me"
}
```

Response:

```json
{
  "access_token": "jwt",
  "refresh_token": "opaque-refresh-token",
  "token_type": "bearer"
}
```

### Refresh login

```text
POST /api/v1/auth/refresh
```

Request:

```json
{
  "refresh_token": "opaque-refresh-token"
}
```

The refresh token is rotated after each successful exchange and cannot be reused.

### Current user

```text
GET /api/v1/auth/me
```

## Device Discovery and Pairing

### Create pairing token

```text
POST /api/v1/device-pairings
```

Authenticated. Used by Electron after discovering a Raspberry Pi on the LAN.

Response:

```json
{
  "pairing_id": "7eecac0b-1e14-4ecb-b1d2-db591ebbe935",
  "pairing_code": "493281",
  "expires_at": "2026-06-23T01:40:00Z"
}
```

### Complete pairing from edge node

```text
POST /api/v1/device-pairings/complete
```

Request:

```json
{
  "pairing_code": "493281",
  "cam_id": "CAM_01",
  "hostname": "ergoquipt-rr",
  "device_type": "raspberry_pi_5_hailo8",
  "metadata": {
    "hailort": "4.23.0"
  }
}
```

### Edge detection lifecycle

The Raspberry Pi lightweight agent stays idle until a paired, authenticated session starts.

The backend sends or exposes these commands for the edge agent:

```text
POST /edge-local/start-detection
POST /edge-local/stop-detection
GET /edge-local/status
GET /edge-local/pairing/info
```

Electron discovery should prefer mDNS service `_ergoquipt-edge._tcp.local` and fall back to LAN probing.

## Workers

### List workers

```text
GET /api/v1/workers
```

### Create worker

```text
POST /api/v1/workers
```

Request:

```json
{
  "employee_number": "EMP-001",
  "name": "Fariz Achmad",
  "department": "Warehouse",
  "position": "Operator"
}
```

### Update worker

```text
PATCH /api/v1/workers/{worker_id}
```

### Deactivate worker

```text
DELETE /api/v1/workers/{worker_id}
```

## Camera Nodes

### List camera nodes

```text
GET /api/v1/camera-nodes
```

### Register camera node

```text
POST /api/v1/camera-nodes
```

Request:

```json
{
  "cam_id": "CAM_01",
  "hostname": "ergoquipt-rr",
  "device_type": "raspberry_pi_5_hailo8",
  "metadata": {
    "hailort": "4.23.0",
    "model": "yolov8s_pose_h8"
  }
}
```

## Sessions

### Create session

```text
POST /api/v1/sessions
```

Request:

```json
{
  "camera_node_ids": ["CAM_01"],
  "notes": "Warehouse line A morning assessment"
}
```

Response:

```json
{
  "id": "5e9f4b53-9f63-4c94-9e30-78d27db4d01e",
  "session_code": "SESSION_20260623_001",
  "status": "created"
}
```

### Start session

```text
POST /api/v1/sessions/{session_id}/start
```

### Stop session

```text
POST /api/v1/sessions/{session_id}/stop
```

Response:

```json
{
  "session_id": "5e9f4b53-9f63-4c94-9e30-78d27db4d01e",
  "status": "review_pending",
  "review_items_created": 8
}
```

### Delete session

```text
DELETE /api/v1/sessions/{session_id}
```

Running sessions must be stopped first. Deletion removes the session's detections, ergonomic events, reviews, assessments, snapshots, reports, worker links, and stored media files.

### Get session detail

```text
GET /api/v1/sessions/{session_id}
```

### List session snapshots

```text
GET /api/v1/sessions/{session_id}/snapshots
```

### List session detections

```text
GET /api/v1/sessions/{session_id}/detections
```

Query parameters:

- `worker_id`
- `cam_id`
- `from`
- `to`
- `limit`
- `cursor`

## Review

### Get review queue

```text
GET /api/v1/sessions/{session_id}/review
```

### Submit review decision

```text
POST /api/v1/sessions/{session_id}/review
```

Request:

```json
{
  "edge_worker_id": "WORKER_E47A",
  "worker_id": "9ffc134d-1ebb-4bc9-b751-e25fbfa62a74",
  "activity_type": "lifting",
  "load_category": "5_10kg",
  "load_score": 1,
  "coupling_score": 1,
  "activity_score": 1,
  "wrist_twist_score": 1
}
```

### Complete session review

```text
POST /api/v1/sessions/{session_id}/complete-review
```

Response:

```json
{
  "session_id": "5e9f4b53-9f63-4c94-9e30-78d27db4d01e",
  "status": "completed",
  "assessments_created": 2
}
```

## Assessments

### List assessments

```text
GET /api/v1/assessments
```

Query parameters:

- `session_id`
- `worker_id`
- `assessment_type`
- `from`
- `to`

### Calculate score preview

```text
POST /api/v1/scoring/preview
```

Request:

```json
{
  "assessment_type": "reba",
  "angles": {
    "neck": 12.0,
    "trunk": 26.0,
    "ua_l": 35.0,
    "ua_r": 42.0,
    "la_l": 88.0,
    "la_r": 91.0,
    "wrist_l": 12.0,
    "wrist_r": 16.0,
    "leg_l": 15.0,
    "leg_r": 17.0
  },
  "manual": {
    "load_score": 1,
    "coupling_score": 1,
    "activity_score": 1,
    "wrist_twist_score": 1
  }
}
```

## Analytics

### Dashboard summary

```text
GET /api/v1/analytics/summary
```

Query parameters:

- `from`
- `to`
- `department`

Response:

```json
{
  "average_rula": 4.8,
  "average_reba": 6.1,
  "peak_risk": "Very High",
  "exposure_duration_seconds": 1820
}
```

### Trends

```text
GET /api/v1/analytics/trends?bucket=daily
```

Valid buckets:

- `daily`
- `weekly`
- `monthly`

### High-risk workers

```text
GET /api/v1/analytics/high-risk-workers
```

### Department comparison

```text
GET /api/v1/analytics/departments
```

## Reports

### Generate report

```text
POST /api/v1/reports
```

Request:

```json
{
  "session_id": "5e9f4b53-9f63-4c94-9e30-78d27db4d01e",
  "report_type": "pdf"
}
```

### Download report

```text
GET /api/v1/reports/{report_id}/download
```
