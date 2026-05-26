/**
 * webcam.js
 * Manages webcam stream, captures frames, sends to /api/analyze.
 * Runs face + gaze detection every 2 seconds.
 * Runs YOLO object detection every 5 seconds.
 */

const WebcamMonitor = (() => {
    const video   = document.getElementById('webcamFeed');
    const canvas  = document.getElementById('webcamCanvas');
    const ctx     = canvas.getContext('2d');

    let stream         = null;
    let analyzeInterval = null;
    let yoloCounter    = 0;      // runs YOLO every 5th call
    let noFaceStart    = null;   // timestamp when face first disappeared
    const NO_FACE_WARN_MS = 5000; // 5 seconds

    // ── Start webcam ───────────────────────────────────────────────────────────
    async function start() {
        try {
            stream = await navigator.mediaDevices.getUserMedia({
                video: { width: 640, height: 480, facingMode: 'user' },
                audio: false
            });
            video.srcObject = stream;
            video.onloadedmetadata = () => {
                canvas.width  = video.videoWidth  || 640;
                canvas.height = video.videoHeight || 480;
                console.log('[Webcam] Stream started:', canvas.width, 'x', canvas.height);
                startAnalysis();
            };
        } catch (err) {
            console.error('[Webcam] Access denied:', err);
            updateStatus('statusFace', 'alert', '👤 Camera: Blocked');
        }
    }

    // ── Capture one frame as base64 ───────────────────────────────────────────
    function captureFrame() {
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        // Use JPEG at 70% quality to reduce payload size
        return canvas.toDataURL('image/jpeg', 0.7);
    }

    // ── Send frame to backend for analysis ────────────────────────────────────
    async function analyzeFrame() {
        const sessionId = document.getElementById('sessionId').value;
        if (!sessionId) return;

        const frame   = captureFrame();
        yoloCounter++;
        const runYolo = (yoloCounter % 5 === 0); // YOLO every ~10 seconds

        try {
            const resp = await fetch('/api/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ session_id: sessionId, frame, run_yolo: runYolo })
            });
            const data = await resp.json();
            handleAnalysisResult(data);
        } catch (err) {
            console.error('[Webcam] Analyze error:', err);
        }
    }

    // ── Process result from backend ───────────────────────────────────────────
    function handleAnalysisResult(data) {
        if (!data.success) return;

        const face = data.face || {};

        // ── Face presence ──────────────────────────────────────────────────────
        if (!face.face_present) {
            if (!noFaceStart) noFaceStart = Date.now();
            const elapsed = Date.now() - noFaceStart;
            if (elapsed > NO_FACE_WARN_MS) {
                showWarning('No face detected! Please stay in front of the camera.');
            }
            updateStatus('statusFace', 'alert', `👤 Face: Not Detected (${Math.floor(elapsed/1000)}s)`);
        } else {
            noFaceStart = null;
            if (face.multiple_faces) {
                updateStatus('statusFace', 'alert', `👤 Multiple Faces: ${face.face_count}`);
                showWarning('Multiple faces detected in the frame!');
            } else {
                updateStatus('statusFace', 'ok', '👤 Face: Detected');
            }
        }

        // ── Gaze / head pose ───────────────────────────────────────────────────
        if (face.looking_away) {
            updateStatus('statusGaze', 'warn',
                `👁️ Looking Away (yaw:${face.yaw}° pitch:${face.pitch}°)`);
        } else {
            updateStatus('statusGaze', 'ok', '👁️ Gaze: Forward');
        }

        // ── Phone detection ────────────────────────────────────────────────────
        if (data.objects && data.objects.phone_detected) {
            showWarning('📱 Mobile phone detected! This is a serious violation.');
        }

        // ── Update cheating score bar ──────────────────────────────────────────
        if (data.logged && data.logged.length > 0) {
            ExamManager.addCheatScore(data.logged.reduce((s, l) => s + l.points, 0));
        }
    }

    // ── Start periodic analysis ────────────────────────────────────────────────
    function startAnalysis() {
        analyzeInterval = setInterval(analyzeFrame, 2000); // every 2 seconds
    }

    function stop() {
        clearInterval(analyzeInterval);
        if (stream) stream.getTracks().forEach(t => t.stop());
    }

    return { start, stop };
})();

// ── Status helper (shared) ─────────────────────────────────────────────────────
function updateStatus(elementId, level, text) {
    const el = document.getElementById(elementId);
    if (!el) return;
    el.className = `status-item ${level}`;
    el.querySelector('.status-text').textContent = text;
}

// ── Warning overlay ────────────────────────────────────────────────────────────
let warningTimeout = null;
function showWarning(message) {
    const overlay = document.getElementById('warningOverlay');
    const msg     = document.getElementById('warningMsg');
    if (!overlay) return;
    msg.textContent = message;
    overlay.style.display = 'flex';
    clearTimeout(warningTimeout);
    warningTimeout = setTimeout(() => { overlay.style.display = 'none'; }, 7000);
}
function dismissWarning() {
    document.getElementById('warningOverlay').style.display = 'none';
}