// Keep desktop discovery filters visible and mobile filters compact.
const filters = document.querySelector('.shop-filters');
if (filters) {
    const desktop = window.matchMedia('(min-width: 992px)');
    const syncFilters = () => { filters.open = desktop.matches || filters.dataset.active === 'true'; };
    syncFilters();
    desktop.addEventListener('change', syncFilters);
}
