'use strict';

(() => {
  const statusDot = document.querySelector('#status-dot');
  const statusText = document.querySelector('#status-text');
  const message = document.querySelector('#message');
  const buttons = [...document.querySelectorAll('[data-action]')];
  const controlButtons = buttons;
  let busy = false;
  let confirmStopUntil = 0;

  function setMessage(text, kind = '') {
    message.textContent = text;
    message.className = `message ${kind}`.trim();
  }

  function setBusy(value) {
    busy = value;
    buttons.forEach(button => { button.disabled = value; });
    document.querySelector('#refresh').disabled = value;
  }

  async function refreshStatus() {
    try {
      const state = await window.e5.api('/status');
      statusDot.className = `dot ${state.running ? 'on' : 'off'}`;
      statusText.textContent = state.running ? '代理服务运行中' : '代理服务已停止';
    } catch (_) {
      statusDot.className = 'dot off';
      statusText.textContent = '暂时无法读取服务状态';
    }
  }

  function errorMessage(error) {
    const detail = error?.data?.error || error?.data?.message;
    return typeof detail === 'string' ? detail : '操作失败，请检查 daed 服务';
  }

  async function runAction(action) {
    if (busy) return;
    if (action === 'subscriptions') {
      setMessage('订阅更新需要 daed 账号验证；当前版本无法在信息屏免登录执行。', 'error');
      return;
    }
    if (action === 'stop' && Date.now() > confirmStopUntil) {
      confirmStopUntil = Date.now() + 4000;
      const button = document.querySelector('[data-action="stop"] span:last-child');
      button.textContent = '再按一次停止';
      setMessage('再次按“再按一次停止”确认，4 秒内有效。');
      window.setTimeout(() => {
        if (Date.now() > confirmStopUntil) {
          button.textContent = '停止';
          confirmStopUntil = 0;
        }
      }, 4100);
      return;
    }

    confirmStopUntil = 0;
    const stopLabel = document.querySelector('[data-action="stop"] span:last-child');
    stopLabel.textContent = '停止';
    const labels = { start: '启动', stop: '停止', reload: '重载配置' };
    setBusy(true);
    setMessage(`正在${labels[action]}…`);
    try {
      const result = await window.e5.api('/action', { body: { action } });
      if (!result?.ok) {
        setMessage(result?.error || result?.message || '操作失败，请检查 daed 服务。', 'error');
      } else {
        setMessage(result.message || '操作已完成。', 'success');
      }
    } catch (error) {
      setMessage(errorMessage(error), 'error');
    } finally {
      await refreshStatus();
      setBusy(false);
    }
  }

  document.querySelector('#refresh').addEventListener('click', refreshStatus);
  document.querySelector('#exit').addEventListener('click', () => window.e5?.exit());
  buttons.forEach(button => button.addEventListener('click', () => runAction(button.dataset.action)));
  controlButtons[0]?.focus();
  window.e5?.onKey(event => {
    const active = controlButtons.indexOf(document.activeElement);
    if (['left', 'right', 'up', 'down'].includes(event.kind)) {
      const current = active < 0 ? 0 : active;
      const rowStart = current < 2 ? 0 : 2;
      const rowEnd = rowStart + 1;
      const column = current % 2;
      const target = event.kind === 'left' ? rowStart + (column === 0 ? 1 : 0) :
        event.kind === 'right' ? rowStart + (column === 1 ? 0 : 1) :
        event.kind === 'up' ? (current < 2 ? current + 2 : current - 2) :
        (current < 2 ? current + 2 : current - 2);
      controlButtons[Math.max(rowStart, Math.min(rowEnd, target))]?.focus();
      return true;
    }
    if (event.kind === 'ok' && document.activeElement instanceof HTMLButtonElement) {
      window.e5?.press(document.activeElement);
      return true;
    }
    return false;
  });
  window.e5?.onBack(() => false);
  refreshStatus();
  window.setInterval(refreshStatus, 15000);
})();
