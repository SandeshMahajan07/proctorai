/**
 * screen_monitor.js
 * Detects tab switches, window blur/focus loss, and fullscreen exit.
 * Logs each violation to /api/log.
 */

const ScreenMonitor = (() => {
    const sessionId = () => document.getElementById('sessionId')?.value;

    async function logViolation(type, description) {
        console.warn(`[Screen] Violation: ${type} — ${description}`);
        try {
            await fetch('/api/log', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id:     sessionId(),
                    violation_type: type,
                    description:    description
                })
            });
            ExamManager.addCheatScore(type === 'TAB_SWITCH' ? 20 : 20);
            showWarning(`⚠️ Suspicious activity: ${description}`);
            updateStatus('statusTab', 'alert', `🖥️ ${description}`);
        } catch (err) {
            console.error('[Screen] Log error:', err);
        }
    }

    function init() {
        // ── Tab visibility change ──────────────────────────────────────────────
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                logViolation('TAB_SWITCH', 'Tab switched or minimized');
            } else {
                updateStatus('statusTab', 'ok', '🖥️ Tab: Active');
            }
        });

        // ── Window blur ────────────────────────────────────────────────────────
        window.addEventListener('blur', () => {
            logViolation('WINDOW_BLUR', 'Window lost focus');
        });
        window.addEventListener('focus', () => {
            updateStatus('statusTab', 'ok', '🖥️ Tab: Active');
        });

        // ── Prevent right-click ────────────────────────────────────────────────
        document.addEventListener('contextmenu', (e) => {
            e.preventDefault();
            logViolation('RIGHT_CLICK', 'Right-click attempted');
        });

        // ── Prevent common copy/paste shortcuts ───────────────────────────────
        document.addEventListener('keydown', (e) => {
            // Block Ctrl+C, Ctrl+V, Ctrl+A, F12, Alt+Tab (detect alt key)
            if ((e.ctrlKey && ['c','v','a','u'].includes(e.key.toLowerCase())) || e.key === 'F12') {
                e.preventDefault();
                logViolation('SHORTCUT_ATTEMPT', `Keyboard shortcut: ${e.key}`);
            }
        });

        console.log('[Screen] Monitor initialized');
    }

    return { init };
})();