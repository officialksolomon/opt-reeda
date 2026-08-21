/* Project specific Javascript goes here. */

document.addEventListener('DOMContentLoaded', () => {
    let mediaRecorder = null;
    let audioChunks = [];
    let currentRecordingBtn = null;
    
    // Function to get CSRF token from cookies
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Audio Playback
    document.addEventListener('click', (e) => {
        const playBtn = e.target.closest('.chunk-audio-play-btn');
        if (playBtn) {
            e.preventDefault();
            const audioUrl = playBtn.getAttribute('data-audio-url');
            if (!audioUrl) return;

            const iconPlay = playBtn.querySelector('.play-icon');
            const iconStop = playBtn.querySelector('.stop-playback-icon');
            const btnText = playBtn.querySelector('.btn-text');

            if (playBtn.audioElement && !playBtn.audioElement.paused) {
                // Stop playback
                playBtn.audioElement.pause();
                playBtn.audioElement.currentTime = 0;
                iconPlay.classList.remove('hidden');    
                iconStop.classList.add('hidden');
                btnText.textContent = 'Play';
            } else {
                // Start playback
                // Cancel any browser native TTS that might be running
                if (window.speechSynthesis) {
                    window.speechSynthesis.cancel();
                    document.dispatchEvent(new CustomEvent('stop-tts'));
                }

                if (!playBtn.audioElement) {
                    playBtn.audioElement = new Audio(audioUrl);
                    
                    let speed = parseFloat(playBtn.getAttribute('data-audio-speed')) || 1.0;
                    const speedSelector = playBtn.parentElement.querySelector('.audio-speed-selector');
                    if (speedSelector) {
                        speed = parseFloat(speedSelector.value) || speed;
                    }
                    playBtn.audioElement.playbackRate = speed;
                    
                    playBtn.audioElement.addEventListener('ended', () => {
                        iconPlay.classList.remove('hidden');
                        iconStop.classList.add('hidden');
                        btnText.textContent = 'Play';
                    });
                }
                playBtn.audioElement.play();
                iconPlay.classList.add('hidden');
                iconStop.classList.remove('hidden');
                btnText.textContent = 'Stop';
            }
        }
    });

    // Handle playback speed change
    document.addEventListener('change', (e) => {
        if (e.target.classList.contains('audio-speed-selector')) {
            const playBtn = e.target.parentElement.querySelector('.chunk-audio-play-btn');
            if (playBtn && playBtn.audioElement) {
                const newSpeed = parseFloat(e.target.value) || 1.0;
                playBtn.audioElement.playbackRate = newSpeed;
            }
        }
    });

    // Audio Recording handled by HTMX now
});
