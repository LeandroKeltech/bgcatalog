(() => {
    const script = document.currentScript;
    const badge = document.getElementById('reservation-notification-count');
    if (!script || !badge) return;
    const inbox = script.dataset.inboxUrl;
    let cursor = Number(script.dataset.cursor || 0);
    let busy = false;
    let stopped = false;
    const button = document.getElementById('enable-reservation-alerts');
    const status = document.getElementById('browser-alert-status');
    const preference = 'bgcatalog-reservation-alerts';
    const supported = 'Notification' in window && window.isSecureContext;
    const enabled = () => {
        try { return localStorage.getItem(preference) === 'on'; } catch { return false; }
    };
    function updateControls() {
        if (!button) return;
        button.disabled = !supported;
        const active = supported && Notification.permission === 'granted' && enabled();
        button.textContent = active ? 'Disable browser alerts' : 'Enable browser alerts';
        status.textContent = !supported ? 'This browser does not support alerts here. Your inbox still receives reservations.'
            : active ? 'Browser alerts are enabled while an admin page is open.'
            : Notification.permission === 'denied' ? 'Alerts are blocked in browser settings. Your inbox still receives reservations.'
            : 'Browser alerts are off. Your inbox still receives reservations.';
    }
    button?.addEventListener('click', async () => {
        if (!supported) return;
        try {
            const active = Notification.permission === 'granted' && enabled();
            const permission = active ? 'granted' : await Notification.requestPermission();
            localStorage.setItem(preference, !active && permission === 'granted' ? 'on' : 'off');
            updateControls();
        } catch { status.textContent = 'Browser alerts could not be enabled. Your inbox still receives reservations.'; }
    });
    async function refresh() {
        if (busy || stopped) return;
        busy = true;
        try {
            const response = await fetch(`${script.dataset.statusUrl}?after=${cursor}`, {credentials: 'same-origin', cache: 'no-store'});
            if (response.redirected || response.status === 403) { stopped = true; return; }
            if (!response.ok) return;
            const data = await response.json();
            badge.textContent = String(data.unread_count);
            badge.hidden = data.unread_count === 0;
            cursor = data.latest_id;
            if (data.new_count > 0) {
                const text = `${data.new_count} new reservation${data.new_count === 1 ? '' : 's'} received.`;
                document.getElementById('reservation-live-alert-text').textContent = text;
                document.getElementById('reservation-live-alert').hidden = false;
                if (supported && Notification.permission === 'granted' && enabled()) {
                    const alert = new Notification('BG Catalog — new reservation', {body: text, tag: 'bgcatalog-reservations'});
                    alert.onclick = () => { window.focus(); window.location.assign(inbox); alert.close(); };
                }
            }
        } catch { /* Keep durable unread alerts available when connectivity returns. */ }
        finally { busy = false; }
    }
    updateControls();
    refresh();
    setInterval(refresh, 30000);
})();
