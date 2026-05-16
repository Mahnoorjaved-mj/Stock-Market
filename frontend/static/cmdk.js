// StockSense — command palette (Cmd/Ctrl+K).
// Fuzzy navigation across pages, tickers, and quick actions.
(function () {
    const ROUTES = [
        { label: 'Dashboard',        kind: 'nav', icon: 'fa-chart-line',  href: '/' },
        { label: 'AI Predictions',   kind: 'nav', icon: 'fa-robot',       href: '/ai_predictions' },
        { label: 'Market Analysis',  kind: 'nav', icon: 'fa-chart-bar',   href: '/market_analysis' },
        { label: 'Watchlist',        kind: 'nav', icon: 'fa-bookmark',    href: '/watchlist' },
        { label: 'Portfolio',        kind: 'nav', icon: 'fa-briefcase',   href: '/portfolio' },
        { label: 'Alerts',           kind: 'nav', icon: 'fa-bell',        href: '/alerts' },
        { label: 'Settings',         kind: 'nav', icon: 'fa-sliders',     href: '/settings' },
        { label: 'Profile',          kind: 'nav', icon: 'fa-user',        href: '/profile' },
        { label: 'Log out',          kind: 'action', icon: 'fa-right-from-bracket',
          action: () => fetch('/logout', { method: 'POST' }).then(() => location.href = '/') },
        { label: 'Toggle theme',     kind: 'action', icon: 'fa-circle-half-stroke',
          action: () => document.getElementById('themeToggle')?.click() },
    ];

    let SYMBOLS = [];
    let openState = false;
    let palette, input, list;
    let selectedIdx = 0;

    function injectStyles() {
        if (document.getElementById('cmdk-style')) return;
        const s = document.createElement('style');
        s.id = 'cmdk-style';
        s.textContent = `
            .cmdk-input {
                width: 100%; padding: 14px 16px; background: transparent;
                border: none; border-bottom: 1px solid var(--border-subtle);
                color: var(--text-primary); font-size: 15px; font-family: inherit;
                outline: none;
            }
            .cmdk-list { list-style: none; padding: 4px; margin: 0; overflow-y: auto; max-height: 50vh; }
            .cmdk-item {
                display: flex; align-items: center; gap: 12px;
                padding: 9px 12px; border-radius: var(--radius-sm);
                cursor: pointer; font-size: 13.5px; color: var(--text-primary);
            }
            .cmdk-item i { color: var(--text-tertiary); width: 16px; text-align: center; }
            .cmdk-item .cmdk-kind {
                margin-left: auto; font-size: 11px; color: var(--text-tertiary);
                text-transform: uppercase; letter-spacing: 0.05em;
            }
            .cmdk-item.selected { background: var(--accent-soft); }
            .cmdk-item.selected i { color: var(--accent); }
            .cmdk-empty { padding: 20px; text-align: center; color: var(--text-tertiary); font-size: 13px; }
        `;
        document.head.appendChild(s);
    }

    function ensureDOM() {
        if (palette) return;
        injectStyles();
        palette = document.createElement('div');
        palette.className = 'ss-modal-backdrop';
        palette.innerHTML = `
            <div class="ss-modal" role="dialog" aria-label="Command palette">
                <input type="text" class="cmdk-input" placeholder="Jump to page, search ticker, run action…" autocomplete="off" spellcheck="false">
                <ul class="cmdk-list"></ul>
            </div>`;
        document.body.appendChild(palette);
        input = palette.querySelector('.cmdk-input');
        list = palette.querySelector('.cmdk-list');
        palette.addEventListener('click', (e) => { if (e.target === palette) close(); });
        input.addEventListener('input', () => { selectedIdx = 0; render(); });
        input.addEventListener('keydown', onKey);
    }

    function loadSymbols() {
        fetch('/api/symbols', { credentials: 'same-origin' })
            .then(r => r.json()).then(d => { SYMBOLS = d.symbols || []; })
            .catch(() => {});
    }

    function score(item, q) {
        if (!q) return 1;
        const ql = q.toLowerCase();
        const label = (item.label || item.symbol || '').toLowerCase();
        const name = (item.name || '').toLowerCase();
        if (label === ql || (item.symbol && item.symbol.toLowerCase() === ql)) return 100;
        if (label.startsWith(ql)) return 60;
        if (label.includes(ql)) return 40;
        if (name.includes(ql)) return 30;
        return 0;
    }

    function candidates(q) {
        const items = [];
        ROUTES.forEach(r => { const s = score(r, q); if (s) items.push({ ...r, _s: s }); });
        if (q && SYMBOLS.length) {
            SYMBOLS.forEach(sym => {
                const s = score(sym, q);
                if (s) items.push({
                    kind: 'ticker', icon: 'fa-chart-line',
                    label: sym.symbol, sublabel: sym.name,
                    href: `/stock/${encodeURIComponent(sym.symbol)}`, _s: s,
                });
            });
        }
        items.sort((a, b) => b._s - a._s);
        return items.slice(0, 12);
    }

    function render() {
        const items = candidates(input.value.trim());
        if (!items.length) {
            list.innerHTML = `<li class="cmdk-empty">No matches</li>`;
            return;
        }
        list.innerHTML = items.map((it, i) => `
            <li class="cmdk-item ${i === selectedIdx ? 'selected' : ''}" data-i="${i}">
                <i class="fas ${it.icon || 'fa-arrow-right'}"></i>
                <span>${it.label}${it.sublabel ? `<span style="color:var(--text-tertiary);margin-left:6px;font-size:12px;">${it.sublabel}</span>` : ''}</span>
                <span class="cmdk-kind">${it.kind}</span>
            </li>`).join('');
        list.querySelectorAll('.cmdk-item').forEach(el => {
            el.addEventListener('mouseenter', () => { selectedIdx = parseInt(el.dataset.i); render(); });
            el.addEventListener('click', () => execute(items[parseInt(el.dataset.i)]));
        });
    }

    function execute(item) {
        if (!item) return;
        close();
        if (item.action) item.action();
        else if (item.href) location.href = item.href;
    }

    function onKey(e) {
        const items = candidates(input.value.trim());
        if (e.key === 'ArrowDown') { e.preventDefault(); selectedIdx = Math.min(items.length - 1, selectedIdx + 1); render(); }
        else if (e.key === 'ArrowUp') { e.preventDefault(); selectedIdx = Math.max(0, selectedIdx - 1); render(); }
        else if (e.key === 'Enter')   { e.preventDefault(); execute(items[selectedIdx]); }
        else if (e.key === 'Escape')  { close(); }
    }

    function open() {
        ensureDOM();
        if (!SYMBOLS.length) loadSymbols();
        palette.classList.add('open');
        openState = true;
        selectedIdx = 0;
        input.value = '';
        render();
        setTimeout(() => input.focus(), 10);
    }
    function close() {
        if (!palette) return;
        palette.classList.remove('open');
        openState = false;
    }

    document.addEventListener('keydown', (e) => {
        if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
            e.preventDefault();
            openState ? close() : open();
        }
    });

    window.openCmdk = open;
})();
