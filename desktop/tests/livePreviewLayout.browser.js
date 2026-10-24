async page => {
  await page.goto('about:blank');
  await page.unrouteAll({ behavior: 'wait' });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.addInitScript(() => {
    const Native = window.WebSocket;
    window.WebSocket = class extends Native {
      constructor(url, protocols) {
        if (String(url).includes(':8000/ws/v1/sessions/')) {
          const socket = { send() {}, close() { this.onclose?.(); } };
          window.__previewLayoutSocket = socket;
          queueMicrotask(() => socket.onopen?.());
          return socket;
        }
        super(url, protocols);
      }
    };
  });
  let cameraCount = 1, status = 'running', frame = 0, newSession = null, patchPath = '', failAssignment = false, frameFailure = '';
  let sessionRows = [];
  const requests = {};
  const cameraId = index => 'CAM_' + String(index + 1).padStart(2, '0');
  const cameras = () => Array.from({ length: cameraCount }, (_, index) => ({
    id: 'camera-' + (index + 1), cam_id: cameraId(index), status: cameraCount === 6 && index === 5 ? 'offline' : 'online',
    metadata_json: { display_name: 'Assembly camera ' + (index + 1), edge_base_url: 'http://edge.test:8765', health: { camera_available: !(cameraCount === 6 && index === 5) } },
  }));
  const session = () => ({ id: 'qa-session', session_code: 'SESSION_QA', status,
    metadata_json: { camera_node_ids: cameras().map(c => c.cam_id), edge_runs: Object.fromEntries(cameras().map(c => [c.cam_id, 'run-' + c.cam_id])) } });
  await page.route('http://127.0.0.1:8000/**', async route => {
    const path = route.request().url().replace('http://127.0.0.1:8000', '').split('?')[0];
    const method = route.request().method();
    const headers = { 'access-control-allow-origin': '*', 'access-control-allow-headers': '*', 'access-control-allow-methods': 'GET,POST,PATCH,OPTIONS' };
    if (method === 'OPTIONS') return route.fulfill({ status: 204, headers });
    if (path.endsWith('/frame')) {
      const id = path.split('/')[4];
      if (id === frameFailure) return route.fulfill({ status: 503, headers, json: { detail: 'Camera unavailable' } });
      requests[id] = (requests[id] || 0) + 1;
      frame++;
      return route.fulfill({ headers, contentType: 'image/svg+xml',
        body: '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360"><rect width="640" height="360" fill="#183a35"/><text x="30" y="170" fill="white" font-size="26">' + id + ' / test frame ' + frame + '</text></svg>' });
    }
    let data;
    if (path === '/health') data = { status: 'ok' };
    else if (path === '/api/v1/auth/me') data = { id: 'qa', full_name: 'Operator QA' };
    else if (path === '/api/v1/camera-nodes') data = cameras();
    else if (path === '/api/v1/workers') data = [
      { id: 'alice', name: 'Alice', employee_number: 'EMP01', is_active: true },
      { id: 'budi', name: 'Budi', employee_number: 'EMP02', is_active: true },
    ];
    else if (path === '/api/v1/sessions' && method === 'POST') {
      newSession = { id: 'qa-new', session_code: 'SESSION_NEW', status: 'created',
        metadata_json: { camera_node_ids: route.request().postDataJSON().camera_node_ids } };
      return route.fulfill({ status: 201, headers, json: newSession });
    } else if (path === '/api/v1/sessions') data = newSession ? [newSession, session()] : [session()];
    else if (path.endsWith('/operator-heartbeat')) return route.fulfill({ status: 204, headers });
    else if (path.endsWith('/stop')) { status = 'review_pending'; data = session(); }
    else if (path === '/api/v1/sessions/qa-new/start') { newSession.status = 'running'; data = newSession; }
    else if (path.endsWith('/start')) { status = 'running'; data = session(); }
    else if (method === 'PATCH' && path.includes('/workers/')) {
      patchPath = path;
      if (failAssignment) { failAssignment = false; return route.fulfill({ status: 503, headers, json: { detail: 'Assignment temporarily unavailable' } }); }
      const row = sessionRows.find(row => path.endsWith('/' + row.id));
      row.worker_id = route.request().postDataJSON().worker_id;
      row.worker_name = row.worker_id === 'alice' ? 'Alice' : row.worker_id === 'budi' ? 'Budi' : null;
      data = row;
    } else if (path.endsWith('/workers')) data = sessionRows;
    else return route.fulfill({ status: 503, headers, json: { detail: 'QA fixture' } });
    return route.fulfill({ headers, json: data });
  });
  async function emit(workers) {
    await page.evaluate(({ count, workers }) => {
      for (let i = 1; i <= count; i++) {
        const cam_id = 'CAM_' + String(i).padStart(2, '0');
        window.__previewLayoutSocket.onmessage({ data: JSON.stringify({
          event_type: 'session_detection', cam_id, session_id: 'SESSION_QA', run_id: 'run-' + cam_id,
          timestamp: Date.now(), frame_id: Date.now(),
          detections: Array.from({ length: workers }, (_, j) => ({ worker_id: 'REID_' + (j + 1), tracking_id: j + 1,
            confidence: .9, bbox: [10, 20, 100, 200], keypoints: { format: 'coco17', points: [] }, metadata: {} })),
        }) });
      }
    }, { count: cameraCount, workers });
  }
  const results = [];
  for (const scenario of [{ count: 1, width: 1120, height: 720 }, { count: 2, width: 1120, height: 720 },
    { count: 4, width: 1440, height: 900 }, { count: 4, width: 1120, height: 720 }, { count: 6, width: 1440, height: 900 }]) {
    cameraCount = scenario.count; status = 'running'; newSession = null;
    sessionRows = cameras().flatMap((camera, index) => [1, 2].map(track => ({
      id: 'sw-' + camera.cam_id + '-' + track, session_id: 'qa-session', camera_node_id: camera.id,
      edge_worker_id: 'REID_' + track, run_id: 'run-' + camera.cam_id, tracking_id: track,
      worker_id: null, worker_name: null, identity_status: 'unconfirmed',
    })));
    await page.goto('about:blank');
    await page.setViewportSize({ width: scenario.width, height: scenario.height });
    await page.goto('http://127.0.0.1:5173');
    await page.evaluate(() => sessionStorage.setItem('ergoquipt.tokens', JSON.stringify({ access_token: 'wall-qa', refresh_token: 'wall-qa' })));
    await page.reload();
    await page.getByRole('button', { name: 'Live Assessment', exact: true }).click();
    await page.waitForFunction(() => Boolean(window.__previewLayoutSocket?.onmessage));
    await page.locator('.cameraStream').first().waitFor();
    await emit(2);
    if (await page.locator('.cameraTile').count() !== Math.min(cameraCount, 4)) throw new Error('Incorrect simultaneous camera count');
    if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1 || document.documentElement.scrollHeight > innerHeight + 2)) throw new Error('Workspace requires page scrolling');
    for (const tile of await page.locator('.cameraTile').all()) {
      const bounds = await tile.boundingBox();
      if (bounds.y < 64 || bounds.y + bounds.height > scenario.height + 1) throw new Error('Camera outside viewport');
    }
    const before = await page.locator('.cameraPreview').first().boundingBox();
    await emit(0);
    await page.waitForTimeout(2200);
    const after = await page.locator('.cameraPreview').first().boundingBox();
    if (Math.abs(before.width - after.width) > 1 || Math.abs(before.height - after.height) > 1) throw new Error('Detection changed camera dimensions');
    await page.screenshot({ path: 'tmp/camera-wall-' + cameraCount + '-' + scenario.width + '.png', fullPage: true });
    results.push(scenario);
  }
  frameFailure = 'camera-3';
  await page.locator('article[aria-label="CAM_03 camera"] [role="status"]').waitFor();
  await page.getByRole('img', { name: 'CAM_02 live camera', exact: true }).waitFor();
  frameFailure = '';
  await page.getByRole('img', { name: 'CAM_03 live camera', exact: true }).waitFor();
  await page.getByRole('button', { name: 'Next cameras', exact: true }).click();
  await page.locator('article[aria-label="CAM_05 camera"]').waitFor();
  if (await page.locator('.cameraTile').count() !== 2) throw new Error('Camera pagination failed');
  await page.getByText('Device offline', { exact: true }).waitFor();
  await page.waitForTimeout(200);
  const hiddenRequests = [1, 2, 3, 4].map(id => requests['camera-' + id] || 0);
  await page.waitForTimeout(400);
  if (hiddenRequests.some((count, index) => count !== (requests['camera-' + (index + 1)] || 0))) throw new Error('Hidden cameras keep requesting preview frames');
  await page.getByRole('button', { name: 'Previous cameras', exact: true }).click();
  await page.getByRole('button', { name: 'Focus camera CAM_02', exact: true }).click();
  if (await page.locator('.cameraTile').count() !== 1) throw new Error('Focus failed');
  await page.getByRole('button', { name: 'Show all cameras from CAM_02', exact: true }).click();
  await emit(2);
  await page.getByRole('button', { name: 'Assign workers for CAM_02', exact: true }).click();
  const inspector = page.getByRole('region', { name: 'Camera workers', exact: true });
  await inspector.waitFor();
  await inspector.getByRole('combobox', { name: 'Assign worker', exact: true }).first().waitFor();
  await inspector.getByRole('combobox', { name: 'Camera', exact: true }).click();
  await page.getByRole('option', { name: 'Assembly camera 5', exact: true }).click();
  await page.locator('article[aria-label="CAM_05 camera"]').waitFor();
  await inspector.getByRole('combobox', { name: 'Camera', exact: true }).click();
  await page.getByRole('option', { name: 'Assembly camera 2', exact: true }).click();
  await page.locator('article[aria-label="CAM_02 camera"]').waitFor();
  await inspector.getByRole('combobox', { name: 'Worker', exact: true }).click();
  await page.getByRole('option', { name: 'REID_2', exact: true }).click();
  if (await inspector.locator('.workerCard').count() !== 1) throw new Error('Worker picker did not isolate the selected track');
  await inspector.getByRole('group', { name: 'REID_2 worker', exact: true }).waitFor();
  await inspector.getByRole('combobox', { name: 'Worker', exact: true }).click();
  await page.getByRole('option', { name: 'REID_1', exact: true }).click();
  if (await page.evaluate(() => document.documentElement.scrollHeight > innerHeight + 2)) throw new Error('Inspector expanded page');
  const row = inspector.getByRole('group', { name: 'REID_1 worker', exact: true });
  failAssignment = true;
  await row.getByRole('combobox', { name: 'Assign worker', exact: true }).click();
  await page.getByRole('option', { name: 'Alice (EMP01)', exact: true }).click();
  await inspector.getByText('Assignment temporarily unavailable', { exact: true }).waitFor();
  await row.getByRole('combobox', { name: 'Assign worker', exact: true }).click();
  await page.getByRole('option', { name: 'Alice (EMP01)', exact: true }).click();
  await row.getByText('Alice', { exact: true }).first().waitFor();
  if (!patchPath.endsWith('/sw-CAM_02-1')) throw new Error('Assignment targeted the wrong camera');
  if (sessionRows.find(row => row.id === 'sw-CAM_01-1').worker_id !== null) throw new Error('Identity leaked between cameras');
  await row.getByText('Measurements', { exact: true }).click();
  await row.getByText('Confidence', { exact: true }).waitFor();
  const geometry = await page.locator('.cameraTile').evaluateAll(tiles => tiles.map(tile => {
    const box = tile.getBoundingClientRect(), title = tile.querySelector('.cameraTileIdentity').getBoundingClientRect();
    const text = tile.querySelector('.cameraTileIdentity .MuiTypography-root');
    const range = document.createRange(); range.selectNodeContents(text);
    return { camera: tile.getAttribute('aria-label'), left: box.left, titleLeft: title.left, titleWidth: title.width, scrollLeft: tile.scrollLeft,
      titleText: text.textContent, textLeft: range.getBoundingClientRect().left, textColor: getComputedStyle(text).color,
      textScrollLeft: text.scrollLeft };
  }));
  if (geometry.some(row => row.titleWidth < 24 || row.titleLeft < row.left || !row.titleText.trim() || row.textLeft < row.titleLeft || row.textScrollLeft !== 0)) throw new Error('Camera title clipped: ' + JSON.stringify(geometry));
  await page.screenshot({ path: 'tmp/camera-wall-inspector.png', fullPage: true });
  await page.getByRole('button', { name: 'Stop session', exact: true }).click();
  await page.getByText('Session stopped.', { exact: true }).waitFor();
  await inspector.getByText('Session inactive', { exact: true }).waitFor();
  await page.getByRole('button', { name: 'Close worker panel', exact: true }).click();
  const video = page.getByRole('switch', { name: 'Video', exact: true });
  await video.uncheck();
  if (await page.locator('.cameraStream').count()) throw new Error('Video toggle left previews mounted');
  await page.waitForTimeout(200);
  const pausedRequests = Object.values(requests).reduce((sum, count) => sum + count, 0);
  await page.waitForTimeout(300);
  if (pausedRequests !== Object.values(requests).reduce((sum, count) => sum + count, 0)) throw new Error('Paused preview keeps requesting frames');
  await video.check();
  await page.getByRole('button', { name: 'New session', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByRole('heading', { name: 'New assessment session', exact: true }).waitFor();
  if (await dialog.getByRole('checkbox').last().isEnabled()) throw new Error('Offline camera can be selected');
  await dialog.getByRole('button', { name: 'Start session', exact: true }).click();
  await dialog.waitFor({ state: 'hidden' });
  if (!newSession || newSession.metadata_json.camera_node_ids.length !== 5 || newSession.metadata_json.camera_node_ids.includes('CAM_06')) throw new Error('New session selection incorrect');
  if (errors.length) throw new Error(errors.join('; '));
  await page.goto('about:blank');
  return { layouts: results, cameraHeaders: geometry, assignmentScope: patchPath, errorRecovery: true, startStop: true, pagination: true, focus: true };
}
