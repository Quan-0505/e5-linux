'use strict';

(() => {
  const $ = selector => document.querySelector(selector);
  const statusDot = $('#status-dot'), statusText = $('#status-text'), message = $('#message');
  const controlsView = $('#controls-view'), subscriptionsView = $('#subscriptions-view');
  const pairing = $('#pairing'), subscriptionList = $('#subscription-list');
  const subscriptionMessage = $('#subscription-message'), pairMessage = $('#pair-message');
  const buttons = [...document.querySelectorAll('[data-action]')];
  let busy = false, confirmStopUntil = 0, pairTimer = 0;

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
      statusDot.className = `dot ${state.running ? 'on' : 'off'}`;
      statusText.textContent = state.running ? 'DAED运行中' : 'DAED已停止';
    } catch (_) { statusDot.className = 'dot off'; statusText.textContent = '暂时无法读取 DAED 状态'; }
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
    if (action === 'stop' && Date.now() > confirmStopUntil) {
      confirmStopUntil = Date.now() + 4000;
      const label = document.querySelector('[data-action="stop"] span:last-child'); label.textContent = '再按一次停止';
      setMessage('再次按“再按一次停止”确认，4 秒内有效。');
      setTimeout(() => { if (Date.now() > confirmStopUntil) { label.textContent = '停止'; confirmStopUntil = 0; } }, 4100); return;
    }
    confirmStopUntil = 0; document.querySelector('[data-action="stop"] span:last-child').textContent = '停止';
    const labels = { start: '启动', stop: '停止', reload: '重载' };
    setBusy(true); setMessage(`正在${labels[action]} DAED…`);
    try {
      const result = await window.e5.api('/action', { body: { action } });
      if (result?.ok === false) throw new Error(errorMessage(result));
      setMessage(result?.message || '操作已完成。', 'success');
    } catch (error) { setMessage(errorMessage(error), 'error'); }
    finally { await refreshStatus(); setBusy(false); }
  }

  $('#refresh').addEventListener('click', refreshStatus);
  $('#exit').addEventListener('click', () => window.e5?.exit());
  buttons.forEach(button => button.addEventListener('click', () => runAction(button.dataset.action)));
  $('#new-qr').addEventListener('click', createQr);
  $('#logout').addEventListener('click', async () => {
    try { await window.e5.api('/logout', { method: 'POST', body: {} }); } catch (_) {}
    await showPairing('已退出登录，请重新扫码。');
  });
  document.querySelectorAll('[data-close-view]').forEach(button => button.addEventListener('click', () => { clearInterval(pairTimer); setView('controls'); }));
  controlsView.querySelector('.controls').setAttribute('data-nav-grid', '');
  buttons.forEach((button, i) => { button.dataset.row = String(Math.floor(i / 2)); button.dataset.col = String(i % 2); });
  $('#refresh').dataset.row = '0'; $('#refresh').dataset.col = '0'; $('#refresh').closest('.status').setAttribute('data-nav-grid', '');
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
  refreshStatus(); setInterval(() => { if (!controlsView.hidden) refreshStatus(); }, 15000);
})();
