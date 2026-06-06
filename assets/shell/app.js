(function () {
  const els = {
    subtitle: document.getElementById('subtitle'),
    status: document.getElementById('status'),
    session: document.getElementById('session'),
    pipe: document.getElementById('pipe'),
    panelName: document.getElementById('panel-name'),
    updatedAt: document.getElementById('updated-at'),
    bodyGrid: document.getElementById('body-grid'),
    contextPane: document.getElementById('context-pane'),
    contextList: document.getElementById('context-list'),
    frame: document.getElementById('stage-frame'),
    choices: document.getElementById('choices'),
  };

  let currentPanel = '';
  let lastChoiceKey = '';
  let writeToken = '';
  const maxPanelInputChars = 20000;

  const statusLabels = {
    idle: '就绪',
    booting: '启动中',
    waiting_for_user: '等待输入',
    learning: '学习中',
    reviewing: '审查中',
    running: '运行中',
    error: '错误',
  };

  function esc(value) {
    return String(value ?? '').replace(/[&<>"']/g, (ch) => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;',
    }[ch]));
  }

  function panelLabel(panel) {
    return String(panel || '').replace(/^panels\//, '') || '无面板';
  }

  function statusLabel(status) {
    const raw = String(status || 'idle');
    return statusLabels[raw] || raw.replace(/_/g, ' ');
  }

  function timeLabel(value) {
    if (!value) return '等待同步';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return `同步 ${new Intl.DateTimeFormat('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    }).format(date)}`;
  }

  function writeHeaders() {
    return {
      'content-type': 'application/json',
      'x-localweb-token': writeToken,
    };
  }

  function renderContext(items) {
    const list = Array.isArray(items) ? items : [];
    if (!list.length) {
      els.contextList.innerHTML = '';
      els.contextPane.classList.add('is-empty');
      els.bodyGrid.classList.add('context-empty');
      return;
    }
    els.contextPane.classList.remove('is-empty');
    els.bodyGrid.classList.remove('context-empty');
    const visible = list.slice(0, 4);
    els.contextList.innerHTML = visible.map((item, index) => {
      const n = String(index + 1).padStart(2, '0');
      return `<li><b>${n}</b><span><strong>${esc(item.label || '上下文')}</strong><em>${esc(item.value || '')}</em></span></li>`;
    }).join('') + (list.length > visible.length
      ? `<li class="context-more"><span>还有 ${list.length - visible.length} 项上下文</span></li>`
      : '');
  }

  function renderChoices(state) {
    const choices = Array.isArray(state.choices) ? state.choices : [];
    const key = JSON.stringify([state.active_choice_id || '', choices]);
    if (key === lastChoiceKey) return;
    lastChoiceKey = key;
    if (!choices.length) {
      els.choices.innerHTML = '';
      els.choices.classList.add('is-empty');
      els.pipe.textContent = '就绪';
      return;
    }
    els.pipe.textContent = '等待输入';
    els.choices.classList.remove('is-empty');
    els.choices.innerHTML = choices.map((choice) => {
      const id = choice.id || choice.value || '';
      const label = choice.label || id;
      return `<button class="choice-btn" data-choice="${esc(id)}" data-label="${esc(label)}">
        <span class="choice-id">${esc(id)}</span><strong>${esc(label)}</strong>
      </button>`;
    }).join('');
    els.choices.querySelectorAll('.choice-btn').forEach((btn) => {
      btn.addEventListener('click', async () => {
        if (btn.disabled) return;
        btn.disabled = true;
        els.pipe.textContent = '发送中';
        try {
          const res = await fetch('/api/choice', {
            method: 'POST',
            headers: writeHeaders(),
            body: JSON.stringify({
              choice_id: state.active_choice_id,
              value: btn.dataset.choice,
              label: btn.dataset.label,
            }),
          });
          if (!res.ok) throw new Error(await res.text());
          els.pipe.textContent = '已发送';
          els.choices.querySelectorAll('.choice-btn').forEach((b) => {
            if (b !== btn) b.disabled = true;
          });
          btn.classList.add('sent');
          const note = document.createElement('div');
          note.className = 'choice-sent-note';
          note.textContent = '已发送到 CLI 等待队列';
          els.choices.appendChild(note);
        } catch (err) {
          els.pipe.textContent = '错误';
          btn.disabled = false;
          btn.classList.add('error');
          btn.title = String(err && err.message ? err.message : err);
        }
      });
    });
  }

  function panelMessagePayload(event) {
    if (event.source !== els.frame.contentWindow) return null;
    const data = event.data;
    if (!data || typeof data !== 'object') return null;
    if (data.localweb !== true || data.type !== 'panel_input') return null;
    const inputId = String(data.input_id || data.id || '').trim();
    const text = typeof data.text === 'string' ? data.text : '';
    if (!inputId || !text.trim() || text.length > maxPanelInputChars) return null;
    const payload = {
      input_id: inputId,
      text,
      panel_id: String(data.panel_id || currentPanel || ''),
    };
    if (data.label != null) payload.label = String(data.label);
    if (data.meta && typeof data.meta === 'object' && !Array.isArray(data.meta)) {
      payload.meta = data.meta;
    }
    return payload;
  }

  async function submitPanelInput(payload) {
    els.pipe.textContent = '发送中';
    const res = await fetch('/api/panel-input', {
      method: 'POST',
      headers: writeHeaders(),
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(await res.text());
    els.pipe.textContent = '已发送';
  }

  function bindPanelBridge() {
    window.addEventListener('message', async (event) => {
      const payload = panelMessagePayload(event);
      if (!payload) return;
      try {
        await submitPanelInput(payload);
      } catch (err) {
        els.pipe.textContent = '错误';
        console.error('LocalWeb panel input failed', err);
      }
    });
  }

  function renderState(state) {
    writeToken = String(state.write_token || '');
    els.subtitle.textContent = state.title || 'HTML 舞台';
    els.status.textContent = statusLabel(state.status);
    els.session.textContent = state.session_id || 'cli-main';
    els.panelName.textContent = panelLabel(state.active_panel);
    els.updatedAt.textContent = timeLabel(state.updated_at);
    renderContext(state.context);
    renderChoices(state);

    const panel = state.active_panel || 'panels/main.html';
    if (panel !== currentPanel) {
      currentPanel = panel;
      const src = panel.startsWith('panels/') ? `/${panel}` : `/panels/${panel}`;
      els.frame.src = `${src}?t=${Date.now()}`;
    }
  }

  async function loadState() {
    const res = await fetch('/api/state', { cache: 'no-store' });
    if (!res.ok) throw new Error(`state ${res.status}`);
    renderState(await res.json());
  }

  function connectStream() {
    if (!('EventSource' in window)) {
      setInterval(loadState, 1200);
      return;
    }
    const stream = new EventSource('/api/stream');
    stream.addEventListener('state', (ev) => {
      try { renderState(JSON.parse(ev.data)); } catch (_) {}
    });
    stream.onerror = () => {
      stream.close();
      setTimeout(connectStream, 1500);
    };
  }

  bindPanelBridge();
  loadState().catch(() => {});
  connectStream();
})();
