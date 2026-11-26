(() => {
    const form = document.querySelector('.catalog-discovery');
    const collection = document.getElementById('collection');
    if (!form || !collection || !window.fetch || !window.AbortController) return;
    const filters = form.querySelector('.shop-filters');
    const desktop = window.matchMedia('(min-width: 992px)');
    const syncFilters = () => { filters.open = desktop.matches || filters.dataset.active === 'true'; };
    syncFilters();
    desktop.addEventListener('change', syncFilters);

    const status = document.getElementById('catalog-status');
    let controller;
    let timer;
    let revision = 0;
    let composing = false;
    const formUrl = () => {
        const url = new URL(form.action);
        url.hash = '';
        url.search = new URLSearchParams(new FormData(form)).toString();
        return url;
    };
    const cancelPending = () => {
        clearTimeout(timer);
        controller?.abort();
        return ++revision;
    };
    const update = async (url, {historyMode = 'push', scroll = false} = {}) => {
        const current = cancelPending();
        controller = new AbortController();
        collection.setAttribute('aria-busy', 'true');
        status.textContent = 'Updating games…';
        status.classList.remove('is-error');
        try {
            const response = await fetch(url, {
                signal: controller.signal,
                headers: {'X-Requested-With': 'XMLHttpRequest'},
            });
            if (!response.ok) throw new Error('Search unavailable');
            const page = new DOMParser().parseFromString(await response.text(), 'text/html');
            if (current !== revision) return;
            const results = page.querySelector('.catalog-results');
            const nextForm = page.querySelector('.catalog-discovery');
            if (!results || !nextForm) throw new Error('Missing search results');
            const focusedId = document.activeElement?.id;
            collection.replaceChildren(results);
            // Keep the search input itself, so typing and keyboard focus stay uninterrupted.
            for (const field of nextForm.elements) {
                const existing = field.name && form.elements.namedItem(field.name);
                if (existing && existing.value !== field.value) existing.value = field.value;
            }
            form.querySelector('.discovery-shortcuts').replaceWith(nextForm.querySelector('.discovery-shortcuts'));
            filters.dataset.active = nextForm.querySelector('.shop-filters').dataset.active;
            filters.querySelector('.discovery-active-indicator')?.remove();
            const nextIndicator = nextForm.querySelector('.discovery-active-indicator');
            if (nextIndicator) filters.querySelector('summary > span').append(nextIndicator);
            if (historyMode !== 'none' && url.href !== window.location.href) {
                window.history[historyMode === 'replace' ? 'replaceState' : 'pushState']({}, '', url);
            }
            if (focusedId && !document.activeElement?.id) {
                document.getElementById(focusedId)?.focus({preventScroll: true});
            }
            status.textContent = results.querySelector('.results-toolbar p').textContent.trim();
            if (scroll) collection.scrollIntoView({block: 'start'});
        } catch (error) {
            if (error.name !== 'AbortError' && current === revision) {
                status.textContent = 'Could not update games. Please try searching again.';
                status.classList.add('is-error');
            }
        } finally {
            if (current === revision) collection.setAttribute('aria-busy', 'false');
        }
    };
    const search = () => {
        cancelPending();
        if (!form.checkValidity()) {
            collection.setAttribute('aria-busy', 'false');
            status.textContent = 'Enter a valid price to update games.';
            return;
        }
        timer = setTimeout(() => update(formUrl(), {historyMode: 'replace'}), 300);
    };
    form.addEventListener('input', (event) => {
        if (!composing && event.target.matches('input[type="search"], input[type="number"]')) search();
    });
    form.addEventListener('compositionstart', () => { composing = true; cancelPending(); });
    form.addEventListener('compositionend', () => { composing = false; search(); });
    form.addEventListener('change', (event) => {
        if (event.target.matches('select') && form.checkValidity()) update(formUrl());
    });
    document.addEventListener('submit', (event) => {
        if (event.target === form) {
            event.preventDefault();
            update(formUrl(), {scroll: true});
        } else if (event.target.matches('.catalog-sort')) {
            event.preventDefault();
            form.elements.namedItem('sort').value = event.target.elements.namedItem('sort').value;
            update(formUrl());
        }
    });
    collection.addEventListener('change', (event) => {
        if (event.target.matches('.catalog-sort select')) {
            form.elements.namedItem('sort').value = event.target.value;
            update(formUrl());
        }
    });
    document.addEventListener('click', (event) => {
        if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        const link = event.target.closest('.discovery-shortcuts a, .discovery-reset, .active-filters a, .catalog-pagination a, .catalog-empty a');
        if (!link || link.origin !== window.location.origin) return;
        event.preventDefault();
        let url = new URL(link.href);
        if (link.closest('.discovery-shortcuts')) {
            const selected = url.searchParams;
            url = formUrl();
            const previous = new URL(window.location.href).searchParams;
            for (const name of ['availability', 'max_price', 'players', 'duration']) {
                if (selected.get(name) !== previous.get(name)) {
                    if (selected.has(name)) url.searchParams.set(name, selected.get(name));
                    else url.searchParams.delete(name);
                }
            }
        }
        update(url, {scroll: Boolean(link.closest('.catalog-pagination'))});
    });
    window.addEventListener('popstate', () => update(new URL(window.location.href), {historyMode: 'none'}));
})();
