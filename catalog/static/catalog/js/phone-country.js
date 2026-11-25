(() => {
    document.querySelectorAll('[data-phone-input]').forEach((phoneInput) => {
        const picker = phoneInput.querySelector('[data-country-picker]');
        const select = picker.querySelector('select');
        if (!select || picker.querySelector('.phone-country-toggle')) return;
        const countries = [...select.options].map((option) => ({
            region: option.value,
            name: option.dataset.country,
            code: option.dataset.dialCode,
        }));
        const normalize = (value) => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
        const makeFlag = (country) => {
            const flag = document.createElement('img');
            flag.src = `${phoneInput.dataset.flagsBase}${country.region.toLowerCase()}.svg`;
            flag.alt = '';
            flag.width = 24;
            flag.height = 18;
            flag.loading = 'lazy';
            return flag;
        };
        const trigger = document.createElement('button');
        trigger.type = 'button';
        trigger.id = `${select.id}_picker`;
        trigger.className = 'phone-country-toggle';
        trigger.setAttribute('aria-haspopup', 'dialog');
        trigger.setAttribute('aria-expanded', 'false');
        trigger.setAttribute('aria-controls', `${select.id}_panel`);
        ['aria-describedby', 'aria-invalid'].forEach((attribute) => {
            if (select.hasAttribute(attribute)) trigger.setAttribute(attribute, select.getAttribute(attribute));
        });
        const panel = document.createElement('div');
        panel.id = `${select.id}_panel`;
        panel.className = 'phone-country-panel';
        panel.hidden = true;
        panel.setAttribute('role', 'dialog');
        panel.setAttribute('aria-label', 'Choose a country code');
        const search = document.createElement('input');
        search.type = 'search';
        search.className = 'form-control phone-country-search';
        search.placeholder = 'Search country or code';
        search.autocomplete = 'off';
        search.setAttribute('role', 'combobox');
        search.setAttribute('aria-label', 'Search country or calling code');
        search.setAttribute('aria-autocomplete', 'list');
        search.setAttribute('aria-expanded', 'false');
        search.setAttribute('aria-controls', `${select.id}_options`);
        const list = document.createElement('div');
        list.id = `${select.id}_options`;
        list.className = 'phone-country-options';
        list.setAttribute('role', 'listbox');
        list.setAttribute('aria-label', 'Countries and calling codes');
        const empty = document.createElement('p');
        empty.className = 'phone-country-empty';
        empty.textContent = 'No countries found.';
        empty.setAttribute('role', 'status');
        empty.hidden = true;
        panel.append(search, list, empty);
        picker.append(trigger, panel);
        select.hidden = true;
        const label = document.getElementById(`${select.id}_label`);
        if (label) label.htmlFor = trigger.id;
        let visible = countries;
        let active = -1;
        const updateTrigger = () => {
            const country = countries.find((country) => country.region === select.value) || countries[0];
            const name = document.createElement('span');
            name.className = 'phone-country-name';
            name.textContent = country.name;
            const code = document.createElement('span');
            code.className = 'phone-dial-code';
            code.textContent = country.code;
            const chevron = document.createElement('span');
            chevron.className = 'phone-country-chevron';
            chevron.setAttribute('aria-hidden', 'true');
            trigger.replaceChildren(makeFlag(country), name, code, chevron);
            trigger.setAttribute('aria-label', `Country code: ${country.name} ${country.code}`);
        };
        const setActive = (index) => {
            active = index;
            [...list.children].forEach((option, optionIndex) => option.classList.toggle('is-active', optionIndex === active));
            if (list.children[active]) {
                search.setAttribute('aria-activedescendant', list.children[active].id);
                list.children[active].scrollIntoView({block: 'nearest'});
            } else search.removeAttribute('aria-activedescendant');
        };
        const close = (restoreFocus = false) => {
            panel.hidden = true;
            trigger.setAttribute('aria-expanded', 'false');
            search.setAttribute('aria-expanded', 'false');
            if (restoreFocus) trigger.focus();
        };
        const choose = (country) => {
            select.value = country.region;
            select.dispatchEvent(new Event('change', {bubbles: true}));
            close(true);
        };
        const render = () => {
            const query = normalize(search.value.trim());
            visible = countries.filter((country) => normalize(`${country.name} ${country.region} ${country.code}`).includes(query));
            const fragment = document.createDocumentFragment();
            visible.forEach((country) => {
                const option = document.createElement('button');
                option.type = 'button';
                option.id = `${select.id}_${country.region}`;
                option.className = 'phone-country-option';
                option.tabIndex = -1;
                option.setAttribute('role', 'option');
                option.setAttribute('aria-selected', String(country.region === select.value));
                const name = document.createElement('span');
                name.textContent = country.name;
                const code = document.createElement('span');
                code.className = 'phone-dial-code';
                code.textContent = country.code;
                option.append(makeFlag(country), name, code);
                option.addEventListener('click', () => choose(country));
                fragment.append(option);
            });
            list.replaceChildren(fragment);
            empty.hidden = visible.length !== 0;
            setActive(query ? (visible.length ? 0 : -1) : visible.findIndex((country) => country.region === select.value));
        };
        const open = () => {
            panel.hidden = false;
            trigger.setAttribute('aria-expanded', 'true');
            search.setAttribute('aria-expanded', 'true');
            search.value = '';
            render();
            search.focus();
        };
        trigger.addEventListener('click', () => panel.hidden ? open() : close());
        trigger.addEventListener('keydown', (event) => {
            if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
                event.preventDefault();
                open();
            }
        });
        search.addEventListener('input', render);
        search.addEventListener('keydown', (event) => {
            if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
                event.preventDefault();
                if (visible.length) setActive((active + (event.key === 'ArrowDown' ? 1 : -1) + visible.length) % visible.length);
            } else if (event.key === 'Enter') {
                event.preventDefault();
                if (visible[active]) choose(visible[active]);
            }
        });
        picker.addEventListener('keydown', (event) => {
            if (event.key === 'Escape' && !panel.hidden) {
                event.preventDefault();
                event.stopPropagation();
                close(true);
            }
        });
        picker.addEventListener('focusout', (event) => {
            if (!picker.contains(event.relatedTarget)) close();
        });
        document.addEventListener('click', (event) => {
            if (!picker.contains(event.target)) close();
        });
        select.addEventListener('change', updateTrigger);
        window.addEventListener('pageshow', updateTrigger);
        updateTrigger();
    });
})();
