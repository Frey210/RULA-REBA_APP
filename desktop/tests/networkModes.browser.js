async page => {
  await page.goto('about:blank');
  await page.unrouteAll({ behavior: 'wait' });
  const calls = [], errors = [];
  let pending = false, mode = 'direct', available = true;
  const camera = { id: 'network-camera', cam_id: 'CAM_01', hostname: 'ergoquipt-rr', status: 'online',
    metadata_json: { device_id: 'network-uuid', edge_base_url: 'http://10.55.1.1:8765', health: { camera_available: true } } };
  page.on('pageerror', error => errors.push(error.message));
  await page.addInitScript(() => {
    window.ergoquipt = { discoverDevices: async () => [{ cam_id: 'CAM_01', device_id: 'network-uuid',
      hostname: 'ergoquipt-rr', address: '10.55.1.1', port: 8765, status: 'idle', paired: true,
      baseUrl: 'http://10.55.1.1:8765' }] };
  });
  await page.route('http://127.0.0.1:8000/**', async route => {
    const request = route.request(), path = request.url().replace('http://127.0.0.1:8000', '').split('?')[0];
    const headers = { 'access-control-allow-origin': '*', 'access-control-allow-headers': '*', 'access-control-allow-methods': '*' };
    if (request.method() === 'OPTIONS') return route.fulfill({ status: 204, headers });
    if (request.method() !== 'GET') calls.push({ path, method: request.method(), body: request.postData() });
    let data = [];
    if (path === '/health') data = { status: 'ok' };
    else if (path.startsWith('/api/v1/analytics/')) return route.fulfill({ status: 503, headers, json: { detail: 'Network QA fixture' } });
    else if (path.endsWith('/auth/me')) data = { id: 'network-qa', full_name: 'Network QA' };
    else if (path.endsWith('/camera-nodes')) data = [camera];
    else if (path.endsWith('/reconnect')) data = camera;
    else if (path.endsWith('/network/status')) data = { wifi: { connection: 'Factory Wi-Fi', address: '192.168.1.38/24' },
      ethernet: { connection: mode === 'direct' ? 'ERGoSIGHT Direct LAN' : 'ERGoSIGHT Site LAN', address: mode === 'direct' ? '10.55.1.1/24' : '192.168.10.80/24' },
      hotspot: false, direct_lan_address: '10.55.1.1/24', provisioning: { state: 'idle' },
      ethernet_mode: { available, mode, pending, target: mode } };
    else if (path.endsWith('/network/wifi')) data = { networks: [{ ssid: 'Factory Wi-Fi', signal: 90, security: 'WPA2', connected: true }] };
    else if (path.endsWith('/network/ethernet/confirm')) { pending = false; data = { status: 'confirmed' }; }
    else if (path.endsWith('/network/ethernet')) { mode = JSON.parse(request.postData()).mode; pending = true; data = { status: 'switching', rollback_seconds: 180 }; }
    return route.fulfill({ headers, json: data });
  });
  await page.goto('http://127.0.0.1:5173');
  await page.evaluate(() => sessionStorage.setItem('ergoquipt.tokens', JSON.stringify({ access_token: 'network-qa', refresh_token: 'network-qa' })));
  await page.reload();
  await page.getByRole('button', { name: 'Devices', exact: true }).click();
  await page.getByRole('button', { name: 'Scan LAN', exact: true }).click();
  await page.getByRole('button', { name: 'Network setup', exact: true }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByRole('combobox', { name: 'Ethernet mode', exact: true }).waitFor();
  if (await dialog.getByRole('button', { name: 'Apply mode', exact: true }).isEnabled()) throw new Error('Unchanged mode can be applied');
  for (const width of [1120, 1440]) {
    await page.setViewportSize({ width, height: width === 1120 ? 720 : 900 });
    const overflow = await dialog.evaluate(element => element.scrollWidth > element.clientWidth + 1);
    if (overflow) throw new Error('Network dialog overflow at ' + width);
    await page.screenshot({ path: `tmp/network-mode-${width}.png`, fullPage: true });
  }
  await dialog.getByRole('combobox', { name: 'Ethernet mode', exact: true }).click();
  await page.getByRole('option', { name: 'Location router / switch (DHCP)', exact: true }).click();
  await dialog.getByRole('button', { name: 'Apply mode', exact: true }).click();
  await page.getByText(/Connect the Pi to the location router or switch/).waitFor();
  await page.getByRole('button', { name: 'Network setup', exact: true }).click();
  await dialog.getByRole('button', { name: 'Keep Ethernet mode', exact: true }).click();
  await dialog.getByText('Ethernet mode saved.', { exact: true }).waitFor();
  await page.screenshot({ path: 'tmp/network-mode-confirmed.png', fullPage: true });
  await dialog.getByRole('button', { name: 'Close', exact: true }).click();
  available = false;
  await page.getByRole('button', { name: 'Network setup', exact: true }).click();
  await dialog.getByText(/install its network-mode helper/).waitFor();
  if (await dialog.getByRole('combobox', { name: 'Ethernet mode', exact: true }).isEnabled()) throw new Error('Outdated helper can change network');
  if (!calls.some(call => call.path.endsWith('/reconnect'))) throw new Error('Scan did not reconnect both directions');
  if (calls.some(call => call.method === 'PATCH' || call.path.includes('/detection/') || call.path.includes('/device-pairings'))) throw new Error('Network scan reset pairing or started inference');
  if (!calls.some(call => call.path.endsWith('/network/ethernet') && JSON.parse(call.body).mode === 'site')) throw new Error('Wrong mode payload');
  if (errors.length) throw new Error(errors.join('; '));
  return { passed: true, calls };
}
