async page => {
  await page.goto('about:blank');
  await page.unrouteAll({ behavior: 'wait' });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.addInitScript(() => {
    const NativeWebSocket = window.WebSocket;
    window.WebSocket = class extends NativeWebSocket {
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
  let frame = 0;
  await page.route('http://127.0.0.1:8000/**', async route => {
    const path = route.request().url().replace('http://127.0.0.1:8000', '').split('?')[0];
    const headers = { 'access-control-allow-origin': '*', 'access-control-allow-headers': '*' };
    if (route.request().method() === 'OPTIONS') return route.fulfill({ status: 204, headers });
    if (path.endsWith('/frame')) {
      const [width, height] = [[640, 360], [1280, 720], [960, 720]][frame++ % 3];
      return route.fulfill({ headers, contentType: 'image/svg+xml',
        body: `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 640 360"><rect width="640" height="360" fill="#183a35"/><text x="24" y="180" fill="white" font-size="22">Layout test / frame ${frame}</text></svg>` });
    }
    let data;
    if (path === '/api/v1/auth/me') data = { id: 'qa', full_name: 'Layout QA' };
    else if (path === '/health') data = { status: 'ok' };
    else if (path === '/api/v1/camera-nodes') data = [{ id: 'qa-camera', cam_id: 'CAM_QA', status: 'online',
      metadata_json: { edge_base_url: 'http://edge.test:8765', display_name: 'QA Camera', health: { camera_available: true } } }];
    else if (path === '/api/v1/sessions') data = [{ id: 'qa-session', session_code: 'SESSION_QA', status: 'created',
      metadata_json: { camera_node_ids: ['CAM_QA'] }, notes: null }];
    else if (path.endsWith('/workers')) data = [];
    else return route.fulfill({ status: 503, headers, json: { detail: 'QA fixture' } });
    return route.fulfill({ headers, json: data });
  });
  await page.goto('http://127.0.0.1:5173');
  await page.evaluate(() => sessionStorage.setItem('ergoquipt.tokens', JSON.stringify({ access_token: 'layout-qa', refresh_token: 'layout-qa' })));
  await page.reload();
  await page.getByRole('button', { name: 'Live Assessment', exact: true }).click();
  await page.getByRole('img', { name: 'CAM_QA live camera' }).waitFor();
  await page.waitForFunction(() => Boolean(window.__previewLayoutSocket?.onmessage));
  const results = [];
  for (const width of [1440, 1280, 1120]) {
    await page.setViewportSize({ width, height: 900 });
    let baseline;
    for (const workers of [0, 1, 6, 0]) {
      await page.evaluate(count => window.__previewLayoutSocket.onmessage({ data: JSON.stringify({
        event_type: 'session_detection', cam_id: 'CAM_QA', session_id: 'SESSION_QA', run_id: 'qa-run',
        timestamp: Date.now(), frame_id: Date.now(), detections: Array.from({ length: count }, (_, index) => ({
          worker_id: 'REID_' + index + '_long_worker_identity_for_layout_regression', tracking_id: index + 1,
          confidence: .9, reid_confidence: .7, bbox: [10, 20, 200, 300], keypoints: { points: [] }, metadata: {},
        })),
      }) }), workers);
      await page.waitForTimeout(workers ? 150 : 2300);
      await page.waitForFunction(count => document.querySelectorAll('.insightPanel .workerCard').length === count, workers);
      const bounds = await page.locator('.cameraPreview').boundingBox();
      const image = await page.locator('.cameraStream').boundingBox();
      if (!baseline) baseline = bounds;
      for (const key of ['x', 'y', 'width', 'height']) {
        if (Math.abs(bounds[key] - baseline[key]) > 1) throw new Error(`Preview ${key} shifts at ${width}px / ${workers} workers: ${baseline[key]} -> ${bounds[key]}`);
      }
      if (Math.abs(image.width - bounds.width) > 1 || Math.abs(image.height - bounds.height) > 1) throw new Error('Image escaped its viewport');
      if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1)) throw new Error('Horizontal overflow');
      const panelsOverlap = await page.evaluate(() => {
        const a = document.querySelector('.livePreview').getBoundingClientRect();
        const b = document.querySelector('.insightPanel').getBoundingClientRect();
        return Math.min(a.right, b.right) - Math.max(a.left, b.left) > 1 && Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) > 1;
      });
      if (panelsOverlap) throw new Error('Preview overlaps insights');
      results.push({ width, workers, preview: [bounds.width, bounds.height] });
      if (workers === 6) await page.screenshot({ path: `tmp/preview-layout-${width}.png`, fullPage: true });
    }
  }
  if (errors.length) throw new Error(errors.join('; '));
  await page.goto('about:blank');
  return results;
}
