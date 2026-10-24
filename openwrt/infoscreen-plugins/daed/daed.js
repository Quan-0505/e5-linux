'use strict';

(() => {
  const $ = selector => document.querySelector(selector);
  const statusDot = $('#status-dot'), statusText = $('#status-text'), message = $('#message');
  const controlsView = $('#controls-view'), subscriptionsView = $('#subscriptions-view');
  const pairing = $('#pairing'), subscriptionList = $('#subscription-list');
  const subscriptionMessage = $('#subscription-message'), pairMessage = $('#pair-message');
  const buttons = [...document.querySelectorAll('[data-action]')];
  const rateButtons = [...document.querySelectorAll('[data-rate-toggle]')];
  const toggleButton = $('#toggle-daed'), toggleLabel = $('#toggle-label'), statusPill = $('.status-pill');
  let busy = false, trafficBusy = false, confirmStopUntil = 0, pairTimer = 0, running = null;
  let rateUnit = 'bits', latestTraffic = null;
  const trafficHistory = { rx: [], tx: [] };
  const HISTORY_SIZE = 24;

  function setMessage(text, kind = '') { message.textContent = text; message.className = `message ${kind}`.trim(); }
  function setBusy(value) { busy = value; [...document.querySelectorAll('button')].forEach(button => { button.disabled = value; }); }
  function errorMessage(error) { return error?.data?.error || error?.data?.message || error?.error || error?.message || '操作失败，请检查 DAED 服务'; }
  function requiresLogin(value) {
    const message = value?.data?.error || value?.error || value?.message || '';
    return value?.status === 401 || value?.data?.status === 401 || /请先扫码登录|登录已过期|请用手机扫码登录|please scan.*login|login.*expired/i.test(message);
  }
  function setView(view) {
    controlsView.hidden = view !== 'controls';
    subscriptionsView.hidden = view !== 'subscriptions';
    if (view === 'subscriptions') $('#new-qr').focus();
  }
  async function refreshStatus() {
    try {
      const state = await window.e5.api('/status');
      running = !!state.running;
      statusDot.className = `dot ${state.running ? 'on' : 'off'}`;
      statusPill.className = `status-pill ${state.running ? 'on' : 'off'}`;
      statusText.textContent = state.running ? '运行中' : '已停止';
      toggleButton.classList.toggle('start', !state.running);
      toggleButton.classList.toggle('stop', !!state.running);
      toggleButton.querySelector('.symbol').textContent = state.running ? '■' : '▶';
      if (Date.now() > confirmStopUntil) toggleLabel.textContent = state.running ? '停止代理' : '启动代理';
    } catch (_) {
      running = null;
      statusDot.className = 'dot'; statusPill.className = 'status-pill unknown';
      statusText.textContent = '状态未知'; toggleLabel.textContent = '刷新状态后操作';
    }
  }
  function formatRate(value) {
    let display = Math.max(0, Number(value) || 0) * (rateUnit === 'bits' ? 8 : 1);
    const units = rateUnit === 'bits'
      ? ['bps', 'Kbps', 'Mbps', 'Gbps']
      : ['B/s', 'KB/s', 'MB/s', 'GB/s'];
    let unit = 0;
    while (display >= 1000 && unit < units.length - 1) { display /= 1000; unit++; }
    if (display === 0) return `0 ${units[unit]}`;
    const digits = display >= 100 ? 0 : display >= 10 ? 1 : display >= 1 ? 2 : 3;
    return `${display.toFixed(digits)} ${units[unit]}`;
  }
  function renderRates() {
    if (!latestTraffic) return;
    $('#download-rate').textContent = formatRate(latestTraffic.downloadRate);
    $('#upload-rate').textContent = formatRate(latestTraffic.uploadRate);
  }
  function formatBytes(value) {
    const bytes = Math.max(0, Number(value) || 0);
    if (bytes >= 1024 ** 3) return `${(bytes / 1024 ** 3).toFixed(1)} GB`;
    if (bytes >= 1024 ** 2) return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
    if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${Math.round(bytes)} B`;
  }
  function paintSparkline(kind, value) {
    const history = trafficHistory[kind];
    history.push(Math.max(0, Number(value) || 0));
    if (history.length > HISTORY_SIZE) history.shift();
    const min = Math.min(...history), max = Math.max(...history);
    const span = Math.max(max - min, max * 0.2, 1), center = (min + max) / 2;
    const points = history.length === 1
      ? `0.0,12.0 100.0,12.0`
      : history.map((sample, index) => {
        const x = index * 100 / (history.length - 1);
        const y = 12 - (sample - center) / span * 18;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      }).join(' ');
    $(`#${kind === 'rx' ? 'download' : 'upload'}-line`).setAttribute('points', points);
  }
  async function refreshTraffic() {
    if (trafficBusy) return;
    trafficBusy = true;
    const note = $('#traffic-note');
    try {
      const traffic = await window.e5.api('/traffic');
      if (!traffic?.available) {
        latestTraffic = null;
        note.textContent = traffic?.message || '流量统计暂不可用'; note.hidden = false;
        $('#download-rate').textContent = '—'; $('#upload-rate').textContent = '—';
        return;
      }
      latestTraffic = traffic;
      renderRates();
      $('#download-total').textContent = formatBytes(traffic.downloadTotal);
      $('#upload-total').textContent = formatBytes(traffic.uploadTotal);
      paintSparkline('rx', traffic.downloadRate); paintSparkline('tx', traffic.uploadRate);
      note.hidden = true;
    } catch (_) {
      note.textContent = '读取流量失败'; note.hidden = false;
    } finally { trafficBusy = false; }
  }
  function renderSubscriptions(items) {
    subscriptionList.replaceChildren(); pairing.hidden = true; subscriptionList.hidden = false;
    if (!items.length) { subscriptionMessage.textContent = '当前账号没有可更新的订阅。'; return; }
    subscriptionMessage.textContent = '点选一个订阅进行更新。';
    items.forEach(item => {
      const button = document.createElement('button'); button.type = 'button'; button.className = 'subscription-item';
      const name = document.createElement('span'); name.textContent = item.name;
      const count = document.createElement('small'); count.textContent = `${item.nodeCount} 个节点`;
      button.append(name, count); button.addEventListener('click', () => refreshSubscription(item)); subscriptionList.append(button);
    });
  }
  async function loadSubscriptions() {
    setView('subscriptions'); subscriptionMessage.textContent = '正在读取订阅…'; subscriptionMessage.className = 'message';
    try {
      const result = await window.e5.api('/subscriptions');
      if (requiresLogin(result)) { await showPairing(result.error || '请用手机扫码登录 daed。'); return; }
      if (result?.ok === false) throw new Error(errorMessage(result));
      renderSubscriptions(Array.isArray(result?.subscriptions) ? result.subscriptions : []);
    } catch (error) {
      if (requiresLogin(error)) await showPairing(errorMessage(error));
      else { subscriptionMessage.textContent = errorMessage(error); subscriptionMessage.className = 'message error'; }
    }
  }
  async function showPairing(text = '请用手机扫码登录 daed。') {
    clearInterval(pairTimer); pairing.hidden = false; subscriptionList.hidden = true;
    subscriptionMessage.textContent = ''; pairMessage.textContent = text;
    await createQr();
    pairTimer = setInterval(async () => {
      try {
        const state = await window.e5.api('/pair-status');
        if (state.loggedIn) { clearInterval(pairTimer); renderSubscriptions(state.subscriptions || []); }
      } catch (_) {}
    }, 3000);
  }
  async function createQr() {
    $('#qr-code').replaceChildren(); pairMessage.textContent = '正在生成安全登录二维码…';
    try {
      const result = await window.e5.api('/pairing', { body: {} });
      if (!result?.qrSvg) throw new Error('二维码生成失败。');
      const parsed = new DOMParser().parseFromString(result.qrSvg, 'image/svg+xml');
      if (parsed.querySelector('parsererror') || parsed.documentElement.localName !== 'svg') throw new Error('二维码格式无效。');
      $('#qr-code').replaceChildren(document.importNode(parsed.documentElement, true));
      pairMessage.textContent = '手机连接 E5 Wi-Fi 后扫码，二维码 5 分钟内有效。';
    } catch (error) { pairMessage.textContent = errorMessage(error); }
  }
  async function refreshSubscription(item) {
    if (busy) return;
    setBusy(true); subscriptionMessage.textContent = `正在更新“${item.name}”…`; subscriptionMessage.className = 'message';
    try {
      const result = await window.e5.api('/action', { body: { action: 'subscriptions', subscriptionId: item.id } });
      if (requiresLogin(result)) { await showPairing(result.error || '登录已过期，请重新扫码。'); return; }
      if (result?.ok === false) throw new Error(errorMessage(result));
      subscriptionMessage.textContent = result?.message || '订阅更新已提交。'; subscriptionMessage.className = 'message success';
    } catch (error) {
      if (requiresLogin(error)) await showPairing(errorMessage(error));
      else { subscriptionMessage.textContent = errorMessage(error); subscriptionMessage.className = 'message error'; }
    } finally { setBusy(false); }
  }
  async function runAction(action) {
    if (busy) return;
    if (action === 'subscriptions') { await loadSubscriptions(); return; }
    if (action === 'toggle' && running == null) { setMessage('正在读取 DAED 状态，请稍后再试。', 'error'); message.hidden = false; return; }
    const actualAction = action === 'toggle' ? (running === false ? 'start' : 'stop') : action;
    if (actualAction === 'stop' && Date.now() > confirmStopUntil) {
      confirmStopUntil = Date.now() + 4000;
      toggleLabel.textContent = '再按一次停止';
      setMessage('再次按下确认停止，4 秒内有效。'); message.hidden = false;
      setTimeout(() => { if (Date.now() > confirmStopUntil) { toggleLabel.textContent = '停止代理'; confirmStopUntil = 0; } }, 4100); return;
    }
    confirmStopUntil = 0;
    const labels = { start: '启动', stop: '停止', reload: '重载配置' };
    setBusy(true); setMessage(`正在${labels[actualAction]} DAED…`); message.hidden = false;
    try {
      const result = await window.e5.api('/action', { body: { action: actualAction } });
      if (result?.ok === false) throw new Error(errorMessage(result));
      setMessage(result?.message || '操作已完成。', 'success');
    } catch (error) { setMessage(errorMessage(error), 'error'); }
    finally { await refreshStatus(); await refreshTraffic(); setBusy(false); }
  }

  $('#exit')?.addEventListener('click', () => window.e5?.exit());
  rateButtons.forEach(button => button.addEventListener('click', () => {
    rateUnit = rateUnit === 'bits' ? 'bytes' : 'bits';
    renderRates();
  }));
  buttons.forEach(button => button.addEventListener('click', () => runAction(button.dataset.action)));
  $('#new-qr').addEventListener('click', createQr);
  $('#logout').addEventListener('click', async () => {
    try { await window.e5.api('/logout', { method: 'POST', body: {} }); } catch (_) {}
    await showPairing('已退出登录，请重新扫码。');
  });
  document.querySelectorAll('[data-close-view]').forEach(button => button.addEventListener('click', () => { clearInterval(pairTimer); setView('controls'); }));
  controlsView.querySelector('.secondary-actions').setAttribute('data-nav-grid', '');
  toggleButton.dataset.row = '0'; toggleButton.dataset.col = '0';
  buttons.filter(button => button !== toggleButton).forEach((button, i) => { button.dataset.row = '1'; button.dataset.col = String(i); });
  buttons[0]?.focus();
  window.e5?.onKey(event => {
    if (!['left', 'right', 'up', 'down'].includes(event.kind) || !(document.activeElement instanceof HTMLButtonElement)) return false;
    const active = document.activeElement, grid = active.closest('[data-nav-grid]');
    if (grid) {
      const r = Number(active.dataset.row || 0), c = Number(active.dataset.col || 0);
      const candidates = [...grid.querySelectorAll('button:not(:disabled)')].filter(b => b !== active).map(b => ({ b, r: Number(b.dataset.row || 0), c: Number(b.dataset.col || 0) }));
      const list = candidates.filter(x => event.kind === 'left' ? x.r === r && x.c < c : event.kind === 'right' ? x.r === r && x.c > c : event.kind === 'up' ? x.r < r : x.r > r).sort((a,b) => Math.abs(a.r-r)+Math.abs(a.c-c)-Math.abs(b.r-r)-Math.abs(b.c-c));
      if (list.length) { list[0].b.focus(); return true; }
    }
    const all = [...document.querySelectorAll('button:not(:disabled)')].filter(b => !b.closest('[hidden]'));
    const index = all.indexOf(active), delta = event.kind === 'left' || event.kind === 'up' ? -1 : 1;
    all[(index + delta + all.length) % all.length]?.focus(); return true;
  });
  window.e5?.onBack(() => { if (!subscriptionsView.hidden) { clearInterval(pairTimer); setView('controls'); return true; } return false; });
  refreshStatus(); refreshTraffic();
  setInterval(() => { if (!controlsView.hidden) refreshStatus(); }, 5000);
  setInterval(() => { if (!controlsView.hidden) refreshTraffic(); }, 2000);
})();
