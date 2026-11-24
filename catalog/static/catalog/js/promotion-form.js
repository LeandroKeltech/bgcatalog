const kindField = document.getElementById('id_kind');
if (kindField) {
    const updateMechanicFields = () => {
        const kind = kindField.value;
        const cartOffer = ['cart_percentage', 'cart_amount', 'cheapest_free', 'cart_extra_percent'].includes(kind);
        document.querySelector('[data-field="minimum_quantity"]').hidden = !cartOffer;
        document.querySelector('[data-field="repeat_free_groups"]').hidden = kind !== 'cheapest_free';
        document.querySelector('[data-field="value"]').hidden = kind === 'cheapest_free';
        const valueField = document.getElementById('id_value');
        valueField.required = kind !== 'cheapest_free';
        if (kind === 'percentage' || kind === 'cart_percentage' || kind === 'cart_extra_percent') valueField.max = '100';
        else valueField.removeAttribute('max');
        document.getElementById('id_minimum_quantity').required = cartOffer;
        document.querySelector('[data-field="games"]').hidden = document.getElementById('id_apply_to_all').checked;
    };
    kindField.addEventListener('change', updateMechanicFields);
    document.getElementById('id_apply_to_all').addEventListener('change', updateMechanicFields);
    updateMechanicFields();
}
