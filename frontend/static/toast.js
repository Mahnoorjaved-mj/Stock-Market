// StockSense — global toast system. Replaces alert() across the app.
// Usage:  toast('Saved', 'success'); toast('Failed', 'error'); toast('Hello')
(function () {
    var stack;

    function ensureStack() {
        if (stack) return stack;
        stack = document.createElement('div');
        stack.id = 'ss-toast-stack';
        stack.setAttribute('role', 'status');
        stack.setAttribute('aria-live', 'polite');
        document.body.appendChild(stack);
        return stack;
    }

    var ICONS = {
        success: 'fa-circle-check',
        error: 'fa-circle-exclamation',
        warn: 'fa-triangle-exclamation',
        info: 'fa-circle-info'
    };

    function toast(message, type, opts) {
        if (typeof document === 'undefined') return;
        type = type || 'info';
        opts = opts || {};
        var duration = typeof opts.duration === 'number' ? opts.duration : 3500;
        var s = ensureStack();
        var el = document.createElement('div');
        el.className = 'ss-toast ' + type;
        var icon = ICONS[type] || ICONS.info;
        el.innerHTML = '<i class="fas ' + icon + '" aria-hidden="true"></i>' +
                       '<span class="ss-toast-msg"></span>';
        el.querySelector('.ss-toast-msg').textContent = message;
        s.appendChild(el);
        // trigger transition
        requestAnimationFrame(function () { el.classList.add('show'); });
        var t = setTimeout(remove, duration);
        function remove() {
            clearTimeout(t);
            el.classList.remove('show');
            setTimeout(function () { if (el.parentNode) el.parentNode.removeChild(el); }, 200);
        }
        el.addEventListener('click', remove);
        return remove;
    }

    window.toast = toast;
})();
