(function () {
  const els = {
    subtitle: document.getElementById('subtitle'),
    status: document.getElementById('status'),
    session: document.getElementById('session'),
    pipe: document.getElementById('pipe'),
    panelName: document.getElementById('panel-name'),
    updatedAt: document.getElementById('updated-at'),
    contextList: document.getElementById('context-list'),
    frame: document.getElementById('stage-frame'),
    choices: document.getElementById('choices'),
  };

  let currentPanel = '';
  let lastChoiceKey = '';

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
    return String(panel || '').replace(/^panels\//, '') || 'none';
  }

  function renderContext(items) {
    const list = Array.isArray(items) ? items : [];
    if (!list.length) {
      els.contextList.innerHTML = '<li><b>01</b><span><strong>No context</strong><em>CLI has not set context yet</em></span></li>';
      return;
    }
    els.contextList.innerHTML = list.map((item, index) => {
      const n = String(index + 1).padStart(2, '0');
      return `<li><b>${n}</b><span><strong>${esc(item.label || 'Context')}</strong><em>${esc(item.value || '')}</em></span></li>`;
    }).join('');
  }

  function renderChoices(state) {
    const choices = Array.isArray(state.choices) ? state.choices : [];
    const key = JSON.stringify([state.active_choice_id || '', choices]);
    if (key === lastChoiceKey) return;
    lastChoiceKey = key;
    if (!choices.length) {
      els.choices.innerHTML = '<div class="choice-empty">NO ACTIVE CHOICES</div>';
      els.pipe.textContent = 'READY';
      return;
    }
    els.pipe.textContent = 'WAITING';
    els.choices.innerHTML = choices.map((choice) => {
      const id = choice.id || choice.value || '';
      const label = choice.label || id;
      return `<button class="choice-btn" data-choice="${esc(id)}" data-label="${esc(label)}">
        <span>${esc(id)}</span><strong>${esc(label)}</strong>
      </button>`;
    }).join('');
    els.choices.querySelectorAll('.choice-btn').forEach((btn) => {
      btn.addEventListener('click', async () => {
        if (btn.disabled) return;
        btn.disabled = true;
        els.pipe.textContent = 'SENDING';
        try {
          const res = await fetch('/api/choice', {
            method: 'POST',
            headers: { 'content-type': 'application/json' },
            body: JSON.stringify({
              choice_id: state.active_choice_id,
              value: btn.dataset.choice,
              label: btn.dataset.label,
            }),
          });
          if (!res.ok) throw new Error(await res.text());
          els.pipe.textContent = 'SENT';
          els.choices.querySelectorAll('.choice-btn').forEach((b) => {
            if (b !== btn) b.disabled = true;
          });
          btn.classList.add('sent');
          const note = document.createElement('div');
          note.className = 'choice-sent-note';
          note.textContent = 'SENT TO INBOX - CLI reads it with localweb wait';
          els.choices.appendChild(note);
        } catch (err) {
          els.pipe.textContent = 'ERROR';
          btn.disabled = false;
          btn.classList.add('error');
          btn.title = String(err && err.message ? err.message : err);
        }
      });
    });
  }

  function renderState(state) {
    els.subtitle.textContent = state.title || 'HTML DECK';
    els.status.textContent = String(state.status || 'idle').toUpperCase();
    els.session.textContent = state.session_id || 'cli-main';
    els.panelName.textContent = panelLabel(state.active_panel);
    els.updatedAt.textContent = state.updated_at || 'not synced';
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

  loadState().catch(() => {});
  connectStream();
})();
