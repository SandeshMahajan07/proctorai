/**
 * exam.js
 * Handles: timer countdown, question navigation,
 * cheating score UI, auto-submit, and integrates all monitors.
 */

// ─── State ─────────────────────────────────────────────────────────────────────
let currentQuestion = 0;
let answers         = {};          // { question_id: selected_answer }
let cheatScore      = 0;
let timerInterval   = null;
let timeLeft        = parseInt(document.getElementById('examDuration')?.value || 1800);
const totalQ        = parseInt(document.getElementById('totalQuestions')?.value || 10);

// ─── ExamManager (shared interface) ───────────────────────────────────────────
const ExamManager = {
    addCheatScore(points) {
        cheatScore += points;
        updateCheatScoreUI();
    }
};

// ─── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    // Start all monitors
    WebcamMonitor.start();
    ScreenMonitor.init();
    AudioMonitor.start();

    // Request fullscreen for anti-cheat
    requestFullscreenMode();

    // Start timer
    startTimer();

    // Listen for radio changes
    document.querySelectorAll('.option-radio').forEach(radio => {
        radio.addEventListener('change', (e) => {
            const qid = parseInt(e.target.dataset.qid);
            answers[qid] = e.target.value;
            markDotAnswered(currentQuestion);
        });
    });

    updateProgress();
});

// ─── Fullscreen ────────────────────────────────────────────────────────────────
function requestFullscreenMode() {
    const el = document.documentElement;
    if (el.requestFullscreen) el.requestFullscreen().catch(() => {});
}

// ─── Timer ────────────────────────────────────────────────────────────────────
function startTimer() {
    timerInterval = setInterval(() => {
        timeLeft--;
        updateTimerDisplay();
        if (timeLeft <= 0) {
            clearInterval(timerInterval);
            autoSubmit();
        }
    }, 1000);
}

function updateTimerDisplay() {
    const mins   = Math.floor(timeLeft / 60).toString().padStart(2, '0');
    const secs   = (timeLeft % 60).toString().padStart(2, '0');
    const el     = document.getElementById('timerDisplay');
    const box    = document.getElementById('timerBox');
    if (!el) return;
    el.textContent = `${mins}:${secs}`;

    box.className = 'timer-box';
    if (timeLeft <= 60)       box.classList.add('danger');
    else if (timeLeft <= 300) box.classList.add('warning');
}

// ─── Question Navigation ───────────────────────────────────────────────────────
function changeQuestion(delta) {
    const next = currentQuestion + delta;
    if (next < 0 || next >= totalQ) return;
    goToQuestion(next);
}

function goToQuestion(idx) {
    // Hide current
    const cards = document.querySelectorAll('.question-card');
    const dots  = document.querySelectorAll('.q-dot');

    if (cards[currentQuestion]) cards[currentQuestion].classList.remove('active');
    if (dots[currentQuestion])  dots[currentQuestion].classList.remove('active');

    currentQuestion = idx;

    if (cards[currentQuestion]) cards[currentQuestion].classList.add('active');
    if (dots[currentQuestion])  dots[currentQuestion].classList.add('active');

    // Update nav buttons
    document.getElementById('btnPrev').disabled = (currentQuestion === 0);
    document.getElementById('btnNext').disabled = (currentQuestion === totalQ - 1);

    updateProgress();
}

function markDotAnswered(idx) {
    const dot = document.querySelectorAll('.q-dot')[idx];
    if (dot) dot.classList.add('answered');
}

function updateProgress() {
    const pct = ((currentQuestion + 1) / totalQ) * 100;
    document.getElementById('progressBar').style.width  = `${pct}%`;
    document.getElementById('progressText').textContent =
        `Question ${currentQuestion + 1} of ${totalQ}`;
}

// ─── Cheating Score UI ─────────────────────────────────────────────────────────
function updateCheatScoreUI() {
    const el  = document.getElementById('cheatScore');
    const bar = document.getElementById('cheatScoreBar');
    if (!el) return;

    el.textContent = cheatScore;

    // Color thresholds
    if (cheatScore === 0)       el.style.color = '#22c55e';
    else if (cheatScore < 100)  el.style.color = '#f59e0b';
    else if (cheatScore < 200)  el.style.color = '#ef4444';
    else                        el.style.color = '#7f1d1d';

    // Bar width (cap at 100%)
    const barPct = Math.min((cheatScore / 300) * 100, 100);
    bar.style.width = `${barPct}%`;
}

// ─── Submit ────────────────────────────────────────────────────────────────────
async function submitExam() {
    if (!confirm('Are you sure you want to submit the exam?')) return;
    await doSubmit();
}

async function autoSubmit() {
    showWarning('⏰ Time is up! Auto-submitting exam...');
    setTimeout(doSubmit, 2000);
}

async function doSubmit() {
    clearInterval(timerInterval);
    WebcamMonitor.stop();
    AudioMonitor.stop();

    const sessionId  = document.getElementById('sessionId').value;
    const answerList = Object.entries(answers).map(([qid, ans]) => ({
        question_id: parseInt(qid),
        answer:      ans
    }));

    try {
        const resp = await fetch('/api/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId, answers: answerList })
        });
        const data = await resp.json();
        if (data.success && data.redirect) {
            window.location.href = data.redirect;
        }
    } catch (err) {
        console.error('[Exam] Submit error:', err);
        alert('Submission failed. Please try again.');
    }
}