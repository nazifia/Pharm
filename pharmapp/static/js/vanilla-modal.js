/* Vanilla modal (Bootstrap 4 markup). No jQuery needed.
 * API: VModal.show(elOrSelector), VModal.hide(elOrSelector)
 * Events (native, bubble): show.bs.modal, shown.bs.modal, hide.bs.modal, hidden.bs.modal
 * Handles [data-toggle="modal"] and [data-dismiss="modal"]; replaces jQuery $.fn.modal if present.
 */
(function () {
    'use strict';
    var open = [];

    function el(x) { return typeof x === 'string' ? document.querySelector(x) : x; }
    function fire(m, name, rel) {
        var e = new CustomEvent(name, { bubbles: true, cancelable: true, detail: { relatedTarget: rel } });
        e.relatedTarget = rel;
        m.dispatchEvent(e);
        // legacy jQuery listeners use event namespaces ("shown.bs.modal")
        if (window.jQuery) {
            var parts = name.split('.');
            window.jQuery(m).triggerHandler(window.jQuery.Event(parts[0] + '.' + parts.slice(1).join('.'), { relatedTarget: rel }));
        }
        return !e.defaultPrevented;
    }

    function show(x, rel) {
        var m = el(x);
        if (!m || m.classList.contains('show')) return;
        if (!fire(m, 'show.bs.modal', rel)) return;
        // Reopening while the previous close is still fading out: cancel that close
        // and drop its (already faded) backdrop, otherwise the pending timer hides
        // the modal we are opening right now.
        if (m._hideTimer) { clearTimeout(m._hideTimer); m._hideTimer = null; }
        if (m._shownTimer) { clearTimeout(m._shownTimer); m._shownTimer = null; }
        if (m._backdrop) { m._backdrop.remove(); m._backdrop = null; }
        var backdrop = document.createElement('div');
        backdrop.className = 'modal-backdrop fade';
        backdrop.setAttribute('data-vmodal-backdrop', 'true');
        document.body.appendChild(backdrop);
        m._backdrop = backdrop;
        m.style.display = 'block';
        m.removeAttribute('aria-hidden');
        m.setAttribute('aria-modal', 'true');
        m.scrollTop = 0;
        document.body.classList.add('modal-open');
        open.push(m);
        void m.offsetWidth; // reflow so the fade transition runs
        m.classList.add('show');
        backdrop.classList.add('show');
        // stack above earlier modals
        var z = 1040 + open.length * 20;
        backdrop.style.zIndex = z;
        m.style.zIndex = z + 10;
        // Remember the timer: if the modal is dismissed during the fade-in we must
        // not fire "shown" afterwards (that would start cameras/focus hidden inputs).
        m._shownTimer = setTimeout(function () {
            m._shownTimer = null;
            if (!m.classList.contains('show')) return;
            fire(m, 'shown.bs.modal', rel);
            var f = m.querySelector('[autofocus]') || m;
            if (f.focus) f.focus({ preventScroll: true });
        }, m.classList.contains('fade') ? 300 : 0);
    }

    /**
     * Remove overlays left behind by a second modal implementation (e.g. a page that
     * still loads Bootstrap's JS next to this file). Without this, closing the modal
     * leaves the page dimmed and unclickable - it looks like the close button failed.
     */
    function clearOrphanOverlays() {
        if (open.length || document.querySelector('.modal.show')) return;
        var strays = document.querySelectorAll('.modal-backdrop');
        for (var i = 0; i < strays.length; i++) strays[i].remove();
        document.body.classList.remove('modal-open');
    }

    function hide(x) {
        var m = el(x);
        if (!m || !m.classList.contains('show')) return;
        if (!fire(m, 'hide.bs.modal')) return;
        if (m._shownTimer) { clearTimeout(m._shownTimer); m._shownTimer = null; }
        m.classList.remove('show');
        if (m._backdrop) m._backdrop.classList.remove('show');
        open = open.filter(function (o) { return o !== m; });
        m._hideTimer = setTimeout(function () {
            m._hideTimer = null;
            // A new show() may have reopened the modal while this was pending.
            if (m.classList.contains('show')) return;
            m.style.display = 'none';
            m.setAttribute('aria-hidden', 'true');
            m.removeAttribute('aria-modal');
            if (m._backdrop) { m._backdrop.remove(); m._backdrop = null; }
            clearOrphanOverlays();
            fire(m, 'hidden.bs.modal');
        }, m.classList.contains('fade') ? 300 : 0);
    }

    document.addEventListener('click', function (e) {
        var t = e.target.closest && e.target.closest('[data-toggle="modal"],[data-dismiss="modal"],[data-bs-toggle="modal"],[data-bs-dismiss="modal"]');
        if (t) {
            if (t.tagName === 'A') e.preventDefault(); // other handlers (e.g. htmx hx-get on the same button) still run
            if (t.dataset.dismiss === 'modal' || t.dataset.bsDismiss === 'modal') hide(t.closest('.modal'));
            else show(t.getAttribute('data-target') || t.getAttribute('data-bs-target') || t.getAttribute('href'), t);
            return;
        }
        // click on the dimmed area (the .modal element itself)
        var top = open[open.length - 1];
        if (top && e.target === top && top.getAttribute('data-backdrop') !== 'static') hide(top);
    }, true);

    document.addEventListener('keydown', function (e) {
        var top = open[open.length - 1];
        if (e.key === 'Escape' && top && top.getAttribute('data-keyboard') !== 'false') hide(top);
    });

    window.VModal = { show: show, hide: hide };

    // Route any leftover $(...).modal('show'|'hide') through the vanilla implementation
    function patch() {
        if (window.jQuery) {
            window.jQuery(document).off('click.bs.modal.data-api'); // Bootstrap 4's own data-api handler
            window.jQuery.fn.modal = function (a) {
                return this.each(function () {
                    if (a === 'hide') hide(this); else if (a === 'show' || a === undefined || typeof a === 'object') show(this);
                    else if (a === 'toggle') (this.classList.contains('show') ? hide : show)(this);
                });
            };
        }
    }
    // Bootstrap 5 style API used by some templates (Bootstrap 4 has no window.bootstrap)
    var B = window.bootstrap = window.bootstrap || {};
    if (!B.Modal) {
        B.Modal = function (x) { this._el = el(x); };
        B.Modal.prototype.show = function () { show(this._el); };
        B.Modal.prototype.hide = function () { hide(this._el); };
        B.Modal.getInstance = B.Modal.getOrCreateInstance = function (x) { var m = el(x); return m ? new B.Modal(m) : null; };
    }

    patch();
    document.addEventListener('DOMContentLoaded', patch);
})();
