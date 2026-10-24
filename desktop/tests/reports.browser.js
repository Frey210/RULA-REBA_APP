async page => {
  await page.goto('about:blank');
  await page.unrouteAll({ behavior: 'wait' });
  let failed = true, generation = 0;
  const requests = [], errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const report = { id: 'qa-report', session_id: 'stopped', status: 'ready', generated_at: '2026-10-24T10:00:00Z',
    metadata_json: { session_code: 'SESSION_20261024_001', worker_count: 3, event_count: 35,
      reviewed_assessment_count: 28, photo_count: 30, omitted_photo_count: 1 },
    download_url: '/api/v1/reports/qa-report/content', archive_url: '/api/v1/reports/qa-report/archive', excel_url: '/api/v1/reports/qa-report/excel' };
  const legacy = { ...report, id: 'legacy-report', archive_url: null, excel_url: null };
  await page.route('http://127.0.0.1:8000/**', async route => {
    const request = route.request(), path = request.url().replace('http://127.0.0.1:8000', '');
    const headers = { 'access-control-allow-origin': '*', 'access-control-allow-headers': '*', 'access-control-allow-methods': 'GET,POST,OPTIONS' };
    if (request.method() === 'OPTIONS') return route.fulfill({ status: 204, headers });
    requests.push({ path, auth: request.headers()['authorization'] });
    let data;
    if (path === '/api/v1/camera-nodes' || path === '/api/v1/workers') data = [];
    if (path === '/health') data = { status: 'ok' };
    if (path === '/api/v1/auth/me') data = { id: 'qa', full_name: 'Operator QA' };
    if (path === '/api/v1/sessions') data = ['stopped', 'running', 'preparing', 'stopping'].map(status => ({
      id: status, session_code: 'SESSION_' + status, status: status === 'stopped' ? 'review_pending' : status,
      notes: 'Assembly station A', metadata_json: {} }));
    if (path === '/api/v1/reports') data = [legacy];
    if (path === '/api/v1/reports/sessions/stopped') { generation++; data = { ...report, id: 'qa-report-' + generation }; }
    if (path.endsWith('/content') || path.endsWith('/archive') || path.endsWith('/excel') || path === '/api/v1/diagnostics') {
      if (failed) { failed = false; return route.fulfill({ status: 503, headers, json: { detail: 'Download unavailable. Try again.' } }); }
      return route.fulfill({ headers, contentType: path.endsWith('/content') ? 'application/pdf' : 'application/zip', body: 'QA download bytes' });
    }
    if (data === undefined) return route.fulfill({ status: 503, headers, json: { detail: 'QA fixture: no analytics' } });
    return route.fulfill({ headers, json: data });
  });
  await page.goto('http://127.0.0.1:5173');
  await page.evaluate(() => sessionStorage.setItem('ergoquipt.tokens', JSON.stringify({ access_token: 'report-qa', refresh_token: 'report-qa' })));
  await page.reload();
  await page.getByRole('button', { name: 'Reports', exact: true }).click();
  await page.getByText('Excel or ZIP is unavailable in this older report. Select Generate Report to create all formats.', { exact: true }).waitFor();
  if (await page.getByRole('button', { name: 'Download ZIP', exact: true }).first().isEnabled()) throw new Error('Legacy ZIP incorrectly enabled');
  await page.getByRole('button', { name: 'Generate Report', exact: true }).click();
  await page.getByText('Report ready.', { exact: true }).waitFor();
  if (generation !== 1) throw new Error('Duplicate report generation');
  await page.getByText('30 photos', { exact: true }).first().waitFor();
  await page.getByText('1 photo unavailable', { exact: true }).first().waitFor();
  if (await page.locator('.reportRow').last().getByRole('button', { name: 'Download Excel', exact: true }).isEnabled()) throw new Error('Old Excel incorrectly enabled');
  const layouts = [];
  for (const viewport of [{ width: 1120, height: 720 }, { width: 1440, height: 900 }]) {
    await page.setViewportSize(viewport);
    await page.screenshot({ path: `tmp/reports-${viewport.width}.png`, fullPage: true });
    if (await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1)) throw new Error('Reports horizontal overflow');
    const buttons = await page.locator('.reportRow button').evaluateAll(nodes => nodes.map(node => {
      const rect = node.getBoundingClientRect();
      return { left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom };
    }));
    if (buttons[0].right > buttons[1].left && buttons[0].bottom > buttons[1].top) throw new Error('Download controls overlap');
    layouts.push(viewport);
  }
  await page.getByRole('combobox', { name: 'Session', exact: true }).click();
  if (await page.getByRole('option').count() !== 1) throw new Error('Active/transitional sessions are reportable');
  await page.getByRole('option').click();
  await page.getByRole('button', { name: 'Download PDF', exact: true }).first().click();
  await page.getByText('Download unavailable. Try again.', { exact: true }).waitFor();
  const pdfDownload = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download PDF', exact: true }).first().click();
  if (!(await pdfDownload).suggestedFilename().endsWith('.pdf')) throw new Error('Wrong PDF extension');
  const zipDownload = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download ZIP', exact: true }).first().click();
  if (!(await zipDownload).suggestedFilename().endsWith('.zip')) throw new Error('Wrong ZIP extension');
  const excelDownload = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download Excel', exact: true }).first().click();
  if (!(await excelDownload).suggestedFilename().endsWith('.xlsx')) throw new Error('Wrong Excel extension');
  await page.getByRole('button', { name: 'Devices', exact: true }).click();
  const diagnosticDownload = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Diagnostics', exact: true }).click();
  if ((await diagnosticDownload).suggestedFilename() !== 'ergosight-diagnostics.zip') throw new Error('Diagnostics download failed');
  if (requests.filter(r => /content$|archive$|excel$|diagnostics$/.test(r.path)).some(r => r.auth !== 'Bearer report-qa')) throw new Error('Download did not use authentication');
  if (errors.length) throw new Error(errors.join('; '));
  await page.goto('about:blank');
  return { layouts, pdf: true, archive: true, excel: true, legacy: true, diagnostics: true, errorRecovery: true, generation };
}
