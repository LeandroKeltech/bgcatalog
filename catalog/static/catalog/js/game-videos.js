document.querySelectorAll('.video-play').forEach((button) => {
    button.addEventListener('click', () => {
        const player = button.closest('.video-player');
        const videoId = player.dataset.videoId;
        if (!/^[A-Za-z0-9_-]{11}$/.test(videoId)) return;
        const iframe = document.createElement('iframe');
        iframe.src = `https://www.youtube-nocookie.com/embed/${videoId}?autoplay=1`;
        iframe.title = player.dataset.videoTitle;
        iframe.allow = 'autoplay; encrypted-media; picture-in-picture';
        iframe.allowFullscreen = true;
        iframe.referrerPolicy = 'strict-origin-when-cross-origin';
        player.replaceChildren(iframe);
        iframe.focus();
    });
});
