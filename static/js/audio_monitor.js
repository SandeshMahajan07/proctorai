/**
 * audio_monitor.js
 * Uses Web Audio API to measure ambient audio RMS levels.
 * Sends periodic audio level reports to /api/audio.
 */

const AudioMonitor = (() => {
    const sessionId = () => document.getElementById('sessionId')?.value;

    let analyserNode  = null;
    let dataArray     = null;
    let audioInterval = null;
    let alertCooldown = false;  // prevent alert spam

    async function start() {
        try {
            const stream  = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
            const ctx     = new (window.AudioContext || window.webkitAudioContext)();
            const source  = ctx.createMediaStreamSource(stream);
            analyserNode  = ctx.createAnalyser();
            analyserNode.fftSize    = 256;
            analyserNode.smoothingTimeConstant = 0.8;
            dataArray = new Uint8Array(analyserNode.frequencyBinCount);
            source.connect(analyserNode);

            // Check audio levels every 3 seconds
            audioInterval = setInterval(checkAudioLevel, 3000);
            console.log('[Audio] Monitor started');
        } catch (err) {
            console.warn('[Audio] Microphone access denied:', err);
            updateStatus('statusAudio', 'warn', '🔊 Mic: Blocked');
        }
    }

    function getRMS() {
        if (!analyserNode) return 0;
        analyserNode.getByteTimeDomainData(dataArray);
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
            const val = (dataArray[i] - 128) / 128;
            sum += val * val;
        }
        return Math.sqrt(sum / dataArray.length) * 1000; // scale for readability
    }

    async function checkAudioLevel() {
        const rms = getRMS();

        if (rms > 50) { // threshold
            updateStatus('statusAudio', 'warn', `🔊 Audio: ${rms.toFixed(0)} (elevated)`);
        } else {
            updateStatus('statusAudio', 'ok', '🔊 Audio: Normal');
        }

        // Send to backend every check
        try {
            const resp = await fetch('/api/audio', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: sessionId(), rms })
            });
            const data = await resp.json();

            if (data.audio?.is_loud && !alertCooldown) {
                showWarning('🔊 Loud audio detected! Please maintain silence during the exam.');
                alertCooldown = true;
                setTimeout(() => { alertCooldown = false; }, 30000); // 30s cooldown
            }
        } catch (err) {
            console.error('[Audio] Report error:', err);
        }
    }

    function stop() {
        clearInterval(audioInterval);
    }

    return { start, stop };
})();