document.getElementById('copy-whatsapp-message')?.addEventListener('click', async () => {
    const message = document.getElementById('whatsapp-message');
    const status = document.getElementById('copy-message-status');
    try {
        await navigator.clipboard.writeText(message.value);
        status.textContent = 'Message copied.';
    } catch {
        message.focus();
        message.select();
        status.textContent = 'Select and copy the message above.';
    }
});
