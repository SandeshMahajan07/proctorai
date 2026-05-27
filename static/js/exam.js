/**
 * exam.js
 * Handles: timer countdown, question navigation,
 * cheating score UI, auto-submit, and integrates all monitors.
 */

// ─── State ─────────────────────────────────────────────────────────────────────
let currentQuestion  = 0;
let answers          = {};          // { question_id: selected_answer }
let cheatScore       = 0;
let timerInterval    = null;
let questionTimeLeft = 60;          // 60 seconds per question
const totalQ         = parseInt(document.getElementById('totalQuestions')?.value || 10);

// ─── ExamManager (shared interface) ───────────────────────────────────────────
const ExamManager = {
    addCheatScore(points) {
        cheatScore += points;
        updateCheatScoreUI();
    }
};

// ─── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    WebcamMonitor.start();
    ScreenMonitor.init();
    AudioMonitor.start();

    requestFullscreenMode();
    startQuestionTimer();

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

// ─── Per-Question Timer ────────────────────────────────────────────────────────
function startQuestionTimer() {
    clearInterval(timerInterval);
    questionTimeLeft = 60;
    updateTimerDisplay();

    timerInterval = setInterval(() => {
        questionTimeLeft--;
        updateTimerDisplay();
        if (questionTimeLeft <= 0) {
            clearInterval(timerInterval);
            onQuestionTimeUp();
        }
    }, 1000);
}

function onQuestionTimeUp() {
    // If there's a next question, auto-advance; otherwise auto-submit
    if (currentQuestion < totalQ - 1) {
        showWarning(`⏰ Time's up for question ${currentQuestion + 1}! Moving to next...`);
        setTimeout(() => {
            goToQuestion(currentQuestion + 1);
            startQuestionTimer();
        }, 1000);
    } else {
        autoSubmit();
    }
}

function updateTimerDisplay() {
    const secs = questionTimeLeft;
    const el   = document.getElementById('timerDisplay');
    const box  = document.getElementById('timerBox');
    if (!el) return;

    el.textContent = `00:${secs.toString().padStart(2, '0')}`;

    box.className = 'timer-box';
    if (secs <= 10)      box.classList.add('danger');
    else if (secs <= 30) box.classList.add('warning');
}

// ─── Question Navigation ───────────────────────────────────────────────────────
function changeQuestion(delta) {
    const next = currentQuestion + delta;
    if (next < 0 || next >= totalQ) return;
    goToQuestion(next);
    startQuestionTimer();   // reset timer on manual navigation too
}

function goToQuestion(idx) {
    const cards = document.querySelectorAll('.question-card');
    const dots  = document.querySelectorAll('.q-dot');

    if (cards[currentQuestion]) cards[currentQuestion].classList.remove('active');
    if (dots[currentQuestion])  dots[currentQuestion].classList.remove('active');

    currentQuestion = idx;

    if (cards[currentQuestion]) cards[currentQuestion].classList.add('active');
    if (dots[currentQuestion])  dots[currentQuestion].classList.add('active');

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

    if (cheatScore === 0)       el.style.color = '#22c55e';
    else if (cheatScore < 100)  el.style.color = '#f59e0b';
    else if (cheatScore < 200)  el.style.color = '#ef4444';
    else                        el.style.color = '#7f1d1d';

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