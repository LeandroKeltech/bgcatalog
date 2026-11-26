(() => {
    const drawerElement = document.getElementById('cartDrawer');
    if (!drawerElement || !window.bootstrap) return;
    const drawer = bootstrap.Offcanvas.getOrCreateInstance(drawerElement);
    const content = drawerElement.querySelector('.cart-drawer-content');
    const badge = document.querySelector('[data-cart-count]');
    const feedback = document.getElementById('cart-drawer-message');
    const showFeedback = (message = '', isError = false) => {
        if (!feedback) return;
        feedback.textContent = message;
        feedback.hidden = !message;
        feedback.classList.toggle('alert-warning', isError);
        feedback.classList.toggle('alert-info', !isError);
    };
    const announce = (message) => {
        let live = document.getElementById('shop-live-message');
        if (!live) {
            live = document.createElement('div'); live.id = 'shop-live-message'; live.className = 'visually-hidden';
            live.setAttribute('role', 'status'); live.setAttribute('aria-live', 'polite'); document.body.append(live);
        }
        live.textContent = message;
    };
    const loadCart = async (open = false) => {
        showFeedback();
        content.setAttribute('aria-busy', 'true');
        try {
            const response = await fetch(`${drawerElement.dataset.cartUrl}?drawer=1`, {headers: {'X-Requested-With': 'XMLHttpRequest'}});
            if (!response.ok) throw new Error('Could not load cart');
            content.innerHTML = await response.text();
            content.setAttribute('aria-busy', 'false');
            if (open) drawer.show();
        } catch (_) {
            content.innerHTML = '<div class="cart-drawer-empty"><p>Your cart could not be loaded. Please try again.</p><a class="btn btn-primary" href="/cart/">Open cart</a></div>';
            content.setAttribute('aria-busy', 'false');
            if (open) drawer.show();
        }
    };
    const updateCount = (count) => {
        if (!badge) return;
        badge.textContent = count;
        badge.hidden = Number(count) === 0;
    };
    document.addEventListener('click', (event) => {
        const open = event.target.closest('[data-cart-open]');
        if (open) { event.preventDefault(); loadCart(true); }
        const close = event.target.closest('[data-cart-close]');
        if (close) { event.preventDefault(); drawer.hide(); }
    });
    document.addEventListener('submit', async (event) => {
        const addForm = event.target.closest('.catalog-add-form');
        const cartForm = event.target.closest('.cart-drawer-quantity');
        const wishForm = event.target.closest('.wishlist-toggle-form');
        const form = addForm || cartForm || wishForm;
        if (!form) return;
        event.preventDefault();
        const button = event.submitter || form.querySelector('button[type="submit"]');
        if (button) button.disabled = true;
        try {
            const action = button && button.hasAttribute('formaction') ? button.formAction : form.action;
            const response = await fetch(action, {method: 'POST', body: new FormData(form), headers: {'X-Requested-With': 'XMLHttpRequest'}});
            const data = await response.json();
            if (!response.ok || !data.ok) throw new Error(data.message || 'Could not update your selection');
            if (button) button.disabled = false;
            announce(data.message);
            if (addForm) {
                updateCount(data.cart_count);
                await loadCart(true);
                if (data.already_in_cart) showFeedback(data.message);
            }
            if (cartForm) { updateCount(data.cart_count); await loadCart(false); }
            if (wishForm) {
                const heart = button.querySelector('i');
                button.classList.toggle('is-saved', data.saved);
                button.setAttribute('aria-pressed', String(data.saved));
                button.setAttribute('aria-label', `${data.saved ? 'Remove' : 'Add'} ${button.dataset.wishlistName || 'game'} ${data.saved ? 'from' : 'to'} wishlist`);
                if (heart) heart.className = `bi ${data.saved ? 'bi-heart-fill' : 'bi-heart'}`;
                const count = document.querySelector('.wishlist-count');
                if (data.wishlist_count && !count) window.location.reload();
                else if (count) { count.textContent = data.wishlist_count; count.hidden = data.wishlist_count === 0; }
                if (!data.saved && window.location.pathname === '/wishlist/') window.location.reload();
            }
        } catch (error) {
            announce(error.message);
            if (addForm || cartForm) {
                await loadCart(true);
                showFeedback(error.message, true);
            }
            if (button) button.disabled = false;
        }
    });
    loadCart(false).then(() => { content.dataset.loaded = 'true'; });
})();
