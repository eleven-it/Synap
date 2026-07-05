/**
 * Notificaciones toast globales Synap (mensajes Django + API JS).
 * Consumir con SynapMessages.initFromDom() tras renderizar partial synap_messages_toast.
 */
(function (global) {
    'use strict';

    var DURATIONS = {
        success: 5000,
        info: 4000,
        warning: 6000,
        error: 8000,
        debug: 3000,
    };

    var ICONS = {
        success: 'check_circle',
        info: 'info',
        warning: 'warning',
        error: 'error',
        debug: 'bug_report',
    };

    var STYLES = {
        success: 'border-emerald-200/90 bg-emerald-50 text-emerald-900 dark:border-emerald-800/60 dark:bg-emerald-950/90 dark:text-emerald-100',
        info: 'border-sky-200/90 bg-sky-50 text-sky-900 dark:border-sky-800/60 dark:bg-sky-950/90 dark:text-sky-100',
        warning: 'border-amber-200/90 bg-amber-50 text-amber-950 dark:border-amber-800/60 dark:bg-amber-950/90 dark:text-amber-100',
        error: 'border-red-200/90 bg-red-50 text-red-900 dark:border-red-800/60 dark:bg-red-950/90 dark:text-red-100',
        debug: 'border-slate-200/90 bg-slate-50 text-slate-900 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100',
    };

    var ICON_COLORS = {
        success: 'text-emerald-600 dark:text-emerald-400',
        info: 'text-sky-600 dark:text-sky-400',
        warning: 'text-amber-600 dark:text-amber-400',
        error: 'text-red-600 dark:text-red-400',
        debug: 'text-slate-500 dark:text-slate-400',
    };

    function parseLevel(tags) {
        var t = String(tags || '');
        if (t.indexOf('error') !== -1) { return 'error'; }
        if (t.indexOf('success') !== -1) { return 'success'; }
        if (t.indexOf('warning') !== -1) { return 'warning'; }
        if (t.indexOf('info') !== -1) { return 'info'; }
        if (t.indexOf('debug') !== -1) { return 'debug'; }
        return 'info';
    }

    function ensureRoot() {
        var root = document.getElementById('synap-messages-root');
        if (root) { return root; }
        root = document.createElement('div');
        root.id = 'synap-messages-root';
        root.className = 'pointer-events-none fixed top-[3.75rem] right-3 z-[100] flex w-[min(100%,22rem)] flex-col gap-2 sm:right-4 md:top-20';
        root.setAttribute('aria-live', 'polite');
        root.setAttribute('aria-atomic', 'false');
        document.body.appendChild(root);
        return root;
    }

    function dismiss(el) {
        if (!el || el.classList.contains('synap-message-leaving')) { return; }
        el.classList.add('synap-message-leaving', 'opacity-0', 'translate-x-3');
        global.setTimeout(function () {
            el.remove();
            var root = document.getElementById('synap-messages-root');
            if (root && !root.children.length) { root.remove(); }
        }, 280);
    }

    function bindDismiss(el, duration) {
        var timer = global.setTimeout(function () { dismiss(el); }, duration);
        var closeBtn = el.querySelector('.synap-message-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', function () {
                global.clearTimeout(timer);
                dismiss(el);
            });
        }
        el.addEventListener('mouseenter', function () { global.clearTimeout(timer); });
        el.addEventListener('mouseleave', function () {
            timer = global.setTimeout(function () { dismiss(el); }, 1800);
        });
    }

    function buildToast(message, level, duration) {
        level = level || 'info';
        duration = duration || DURATIONS[level] || 5000;
        var root = ensureRoot();
        var el = document.createElement('div');
        el.className = [
            'synap-message-toast pointer-events-auto flex items-start gap-2.5 rounded-xl border px-3.5 py-3 shadow-lg',
            'transition-all duration-300 ease-out translate-x-0 opacity-100',
            STYLES[level] || STYLES.info,
        ].join(' ');
        el.setAttribute('role', level === 'error' ? 'alert' : 'status');
        el.setAttribute('data-level', level);
        el.innerHTML = [
            '<span class="material-icons shrink-0 text-xl ', ICON_COLORS[level] || ICON_COLORS.info, '" aria-hidden="true">',
            ICONS[level] || ICONS.info,
            '</span>',
            '<p class="min-w-0 flex-1 pt-0.5 text-sm font-medium leading-snug">', message, '</p>',
            '<button type="button" class="synap-message-close -mr-1 shrink-0 rounded-md p-0.5 opacity-60 transition-opacity hover:opacity-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-purple-500" aria-label="Cerrar notificación">',
            '<span class="material-icons text-lg" aria-hidden="true">close</span>',
            '</button>',
        ].join('');
        root.appendChild(el);
        bindDismiss(el, duration);
        return el;
    }

    function initFromDom() {
        var root = document.getElementById('synap-messages-root');
        if (!root) { return; }
        var seen = new Set();
        root.querySelectorAll('.synap-message-toast').forEach(function (el) {
            var textEl = el.querySelector('[data-message-text]');
            var text = textEl ? textEl.textContent.trim() : el.textContent.trim();
            if (seen.has(text)) {
                el.remove();
                return;
            }
            seen.add(text);
            var level = el.getAttribute('data-level') || 'info';
            var duration = parseInt(el.getAttribute('data-duration'), 10) || DURATIONS[level] || 5000;
            bindDismiss(el, duration);
        });
        if (!root.children.length) { root.remove(); }
    }

    function show(message, level, duration) {
        if (!message) { return null; }
        return buildToast(String(message), level || 'info', duration);
    }

    global.SynapMessages = {
        show: show,
        initFromDom: initFromDom,
        dismiss: dismiss,
    };

    /* Alias usado en pantallas legacy */
    if (typeof global.showToast !== 'function') {
        global.showToast = function (message, type) {
            var level = type === 'danger' ? 'error' : (type || 'info');
            return show(message, level);
        };
    }
})(window);
