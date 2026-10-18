'use strict';

(() => {
  const frame = document.querySelector('#console');
  const host = location.hostname;
  const consoleUrl = new URL(`http://${host}:2023/`);

  function loadConsole() {
    frame.src = consoleUrl.href;
  }

  document.querySelector('#refresh').addEventListener('click', loadConsole);
  document.querySelector('#exit').addEventListener('click', () => window.e5?.exit());
  window.e5?.onBack(() => false);
  loadConsole();
})();
