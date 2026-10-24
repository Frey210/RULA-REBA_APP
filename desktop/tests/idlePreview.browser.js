async page => {
  await page.goto('about:blank');
  await page.unrouteAll({ behavior: 'wait' });
  await page.addInitScript(() => {
    const Native = window.WebSocket;
    window.WebSocket = class extends Native {
      constructor(url, protocols) {
        if (String(url).includes(':8000/ws/v1/sessions/')) {
          const socket = { send() {}, close() { this.onclose?.(); } };
          queueMicrotask(() => socket.onopen?.());
          return socket;
        }
        super(url, protocols);
      }
    };
  });
  const errors = [], mutations = [], frames = {};
  page.on('pageerror', error => errors.push(error.message));
  const cameras = [1, 2, 3].map(number => ({ id: 'camera-' + number, cam_id: 'CAM_0' + number,
    status: number === 1 ? 'offline' : 'online', metadata_json: { display_name: 'Camera ' + number,
      health: { camera_available: number !== 1 } } }));
  let sessions = [{ id: 'saved', session_code: 'SAVED_SESSION', status: 'review_pending',
    metadata_json: { camera_node_ids: ['CAM_01'], edge_runs: {} } }];
  await page.route('http://127.0.0.1:8000/**', async route => {
    const request = route.request(), path = request.url().replace('http://127.0.0.1:8000', '').split('?')[0];
    const headers = { 'access-control-allow-origin': '*', 'access-control-allow-headers': '*', 'access-control-allow-methods': '*' };
    if (request.method() === 'OPTIONS') return route.fulfill({ status: 204, headers });
    if (request.method() !== 'GET') mutations.push({ path, method: request.method(), data: request.postDataJSON() });
    if (path.endsWith('/frame')) {
      const id = path.split('/')[4];
      frames[id] = (frames[id] || 0) + 1;
      return route.fulfill({ headers, contentType: 'image/svg+xml', body: `<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360"><rect width="640" height="360" fill="#16484b"/><text x="20" y="180" fill="white" font-size="28">${id}</text></svg>` });
    }
    let data;
    if (path === '/health') data = { status: 'ok' };
    else if (path === '/api/v1/auth/me') data = { id: 'qa', full_name: 'Preview QA' };
    else if (path === '/api/v1/camera-nodes') data = cameras;
    else if (path === '/api/v1/workers' || path.endsWith('/workers')) data = [];
    else if (path === '/api/v1/sessions' && request.method() === 'POST') {
      const session = { id: 'new', session_code: 'NEW_SESSION', status: 'created', metadata_json: { camera_node_ids: request.postDataJSON().camera_node_ids } };
      sessions = [session, ...sessions]; data = session;
    } else if (path === '/api/v1/sessions') data = sessions;
    else if (path.endsWith('/operator-heartbeat')) return route.fulfill({ status: 204, headers });
    else if (path.endsWith('/start') || path.endsWith('/stop')) {
      const session = sessions.find(row => path.includes('/' + row.id + '/'));
      session.status = path.endsWith('/start') ? 'running' : 'review_pending'; data = session;
    } else return route.fulfill({ status: 503, headers, json: { detail: 'QA fixture' } });
    return route.fulfill({ headers, json: data });
  });
  async function open() {
    await page.goto('http://127.0.0.1:5173');
    await page.evaluate(() => sessionStorage.setItem('ergoquipt.tokens', JSON.stringify({ access_token: 'preview-qa', refresh_token: 'preview-qa' })));
    await page.reload();
    await page.getByRole('button', { name: 'Live Assessment', exact: true }).click();
    await page.getByRole('combobox', { name: 'Preview camera', exact: true }).waitFor();
  }
  async function choose(name) {
    await page.getByRole('combobox', { name: 'Preview camera', exact: true }).click();
    await page.getByRole('option', { name, exact: true }).click();
  }
  await open();
  if (await page.getByRole('button', { name: 'Start session', exact: true }).isEnabled()) throw new Error('Offline saved session can start');
  await choose('Camera 2 (CAM_02)');
  await page.getByRole('img', { name: 'CAM_02 live camera', exact: true }).waitFor();
  if (await page.getByRole('button', { name: 'Start session', exact: true }).isEnabled()) throw new Error('Preview selection changed session readiness');
  await choose('Camera 3 (CAM_03)');
  await page.getByRole('img', { name: 'CAM_03 live camera', exact: true }).waitFor();
  await page.waitForTimeout(200);
  const oldRequests = frames['camera-2'];
  await page.waitForTimeout(400);
  if (frames['camera-2'] !== oldRequests) throw new Error('Previous camera still polling');
  if (mutations.length) throw new Error('Preview caused a write or inference start: ' + JSON.stringify(mutations));
  if (sessions[0].metadata_json.camera_node_ids.join(',') !== 'CAM_01') throw new Error('Stored session cameras changed');
  for (const viewport of [{ width: 1120, height: 720 }, { width: 1440, height: 900 }]) {
    await page.setViewportSize(viewport);
    if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1 || document.documentElement.scrollHeight > innerHeight + 2)) throw new Error('Idle workspace overflow');
    await page.screenshot({ path: `tmp/idle-preview-${viewport.width}.png`, fullPage: true });
  }
  await choose('All paired cameras');
  if (await page.locator('.cameraTile').count() !== 3) throw new Error('All paired cameras missing');
  await choose('Session cameras');
  await page.getByRole('article', { name: 'CAM_01 camera', exact: true }).waitFor();
  await page.getByText('Device offline', { exact: true }).waitFor();
  if (frames['camera-1']) throw new Error('Offline camera was polled');
  await choose('Camera 3 (CAM_03)');
  await page.getByRole('button', { name: 'New session', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByRole('checkbox').last().uncheck();
  await dialog.getByRole('button', { name: 'Start session', exact: true }).click();
  await dialog.waitFor({ state: 'hidden' });
  await page.getByRole('article', { name: 'CAM_02 camera', exact: true }).waitFor();
  if (await page.getByRole('combobox', { name: 'Preview camera', exact: true }).count()) throw new Error('Idle selector present during inference');
  if (await page.locator('.cameraTile').count() !== 1) throw new Error('Running wall includes a non-session camera');
  await page.getByRole('button', { name: 'Stop session', exact: true }).click();
  await page.getByRole('combobox', { name: 'Preview camera', exact: true }).waitFor();
  await choose('Camera 3 (CAM_03)');
  await page.getByRole('img', { name: 'CAM_03 live camera', exact: true }).waitFor();
  sessions = [];
  await open();
  await choose('Camera 2 (CAM_02)');
  await page.getByRole('img', { name: 'CAM_02 live camera', exact: true }).waitFor();
  if (errors.length) throw new Error(errors.join('; '));
  await page.goto('about:blank');
  return { idleSwitch: true, noSession: true, offline: true, stopsOldPolling: true, noPreviewWrites: true, activeSessionScope: true };
}
