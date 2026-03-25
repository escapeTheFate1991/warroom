/**
 * Voice I/O — Mic button + Conversation mode button for OpenClaw Control UI
 * 🎙️ = Push-to-talk dictation (transcribe → paste into chat)
 * 🌊 = Conversation mode (always-listening with wake word, TTS responses)
 */
(function () {
  'use strict';

  const VOICE_SERVER = `http://${window.location.hostname}:18793`;
  const AUTO_SEND = false;

  // ── State ─────────────────────────────────────────────────────────────
  let mediaRecorder = null;
  let audioChunks = [];
  let isRecording = false;
  let micButton = null;
  let convoButton = null;
  let convoActive = false;
  let convoCheckInterval = null;

  // ── Mic Button (Dictation) ────────────────────────────────────────────
  function createMicButton() {
    const btn = document.createElement('button');
    btn.id = 'voice-io-mic';
    btn.innerHTML = '🎙️';
    btn.title = 'Push to talk — dictate to text';
    btn.setAttribute('aria-label', 'Voice dictation');
    applyButtonStyle(btn, '#1a1a2e', '120px');
    btn.addEventListener('mouseenter', () => { if (!isRecording) btn.style.background = '#2a2a4e'; });
    btn.addEventListener('mouseleave', () => { if (!isRecording) btn.style.background = '#1a1a2e'; });
    btn.addEventListener('click', toggleRecording);
    return btn;
  }

  // ── Conversation Button (Waveform) ────────────────────────────────────
  function createConvoButton() {
    const btn = document.createElement('button');
    btn.id = 'voice-io-convo';
    btn.innerHTML = `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M2 12h2"/>
      <path d="M6 8v8"/>
      <path d="M10 4v16"/>
      <path d="M14 6v12"/>
      <path d="M18 8v8"/>
      <path d="M22 12h-2"/>
    </svg>`;
    btn.title = 'Conversation mode — always-listening with wake word "Friday"';
    btn.setAttribute('aria-label', 'Conversation mode');
    applyButtonStyle(btn, '#1a1a2e', '176px');
    btn.addEventListener('mouseenter', () => { if (!convoActive) btn.style.background = '#2a2a4e'; });
    btn.addEventListener('mouseleave', () => { if (!convoActive) btn.style.background = '#1a1a2e'; });
    btn.addEventListener('click', toggleConversation);
    return btn;
  }

  function applyButtonStyle(btn, bg, bottom) {
    Object.assign(btn.style, {
      position: 'fixed',
      bottom: bottom,
      right: '24px',
      zIndex: '10000',
      width: '48px',
      height: '48px',
      borderRadius: '50%',
      border: '2px solid #555',
      background: bg,
      color: '#fff',
      fontSize: '22px',
      cursor: 'pointer',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      transition: 'all 0.2s ease',
      boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
    });
  }

  // ── Conversation Mode Toggle ──────────────────────────────────────────
  async function toggleConversation() {
    if (convoActive) {
      await stopConversation();
    } else {
      await startConversation();
    }
  }

  async function startConversation() {
    try {
      convoButton.disabled = true;
      convoButton.style.opacity = '0.5';
      showToast('Starting conversation mode...', 'info');

      const res = await fetch(`${VOICE_SERVER}/conversation/start`, { method: 'POST' });
      const data = await res.json();

      if (data.status === 'ok' || data.status === 'already_running') {
        convoActive = true;
        setConvoButtonState(true);
        showToast('🎧 Conversation mode ON — say "Friday" to talk', 'success');
        // Poll status periodically
        convoCheckInterval = setInterval(checkConvoStatus, 10000);
      } else {
        showToast(`Failed: ${data.error || 'unknown error'}`, 'error');
      }
    } catch (err) {
      showToast('Voice server unreachable', 'error');
    } finally {
      convoButton.disabled = false;
      convoButton.style.opacity = '1';
    }
  }

  async function stopConversation() {
    try {
      await fetch(`${VOICE_SERVER}/conversation/stop`, { method: 'POST' });
    } catch (err) { /* ignore */ }
    convoActive = false;
    setConvoButtonState(false);
    if (convoCheckInterval) {
      clearInterval(convoCheckInterval);
      convoCheckInterval = null;
    }
    showToast('Conversation mode OFF', 'info');
  }

  async function checkConvoStatus() {
    try {
      const res = await fetch(`${VOICE_SERVER}/conversation/status`);
      const data = await res.json();
      if (!data.running) {
        convoActive = false;
        setConvoButtonState(false);
        if (convoCheckInterval) {
          clearInterval(convoCheckInterval);
          convoCheckInterval = null;
        }
      }
    } catch (err) { /* server down */ }
  }

  function setConvoButtonState(active) {
    if (!convoButton) return;
    if (active) {
      convoButton.style.background = '#2ecc71';
      convoButton.style.border = '2px solid #2ecc71';
      convoButton.style.animation = 'voice-io-wave 2s infinite';
      convoButton.title = 'Conversation mode ACTIVE — click to stop';
    } else {
      convoButton.style.background = '#1a1a2e';
      convoButton.style.border = '2px solid #555';
      convoButton.style.animation = 'none';
      convoButton.title = 'Conversation mode — click to start';
    }
  }

  // ── Recording (Dictation) ─────────────────────────────────────────────
  function setRecordingState(recording) {
    isRecording = recording;
    if (!micButton) return;
    if (recording) {
      micButton.style.background = '#e74c3c';
      micButton.style.border = '2px solid #e74c3c';
      micButton.style.animation = 'voice-io-pulse 1.5s infinite';
      micButton.innerHTML = '⏹️';
      micButton.title = 'Recording... click to stop';
    } else {
      micButton.style.background = '#1a1a2e';
      micButton.style.border = '2px solid #555';
      micButton.style.animation = 'none';
      micButton.innerHTML = '🎙️';
      micButton.title = 'Push to talk';
    }
  }

  function setProcessingState() {
    if (!micButton) return;
    micButton.style.background = '#f39c12';
    micButton.style.border = '2px solid #f39c12';
    micButton.innerHTML = '⏳';
    micButton.title = 'Transcribing...';
    micButton.disabled = true;
  }

  function clearProcessingState() {
    if (!micButton) return;
    micButton.disabled = false;
    setRecordingState(false);
  }

  async function toggleRecording() {
    if (isRecording) {
      stopRecording();
    } else {
      await startRecording();
    }
  }

  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true }
      });
      audioChunks = [];
      mediaRecorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
          ? 'audio/webm;codecs=opus' : 'audio/webm'
      });
      mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunks.push(e.data); };
      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        const blob = new Blob(audioChunks, { type: 'audio/webm' });
        await sendForTranscription(blob);
      };
      mediaRecorder.start(100);
      setRecordingState(true);
    } catch (err) {
      showToast('Mic access denied. Check browser permissions.', 'error');
    }
  }

  function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop();
    setRecordingState(false);
  }

  async function sendForTranscription(blob) {
    setProcessingState();
    try {
      const formData = new FormData();
      formData.append('audio', blob, 'recording.webm');
      const res = await fetch(`${VOICE_SERVER}/transcribe`, { method: 'POST', body: formData });
      const data = await res.json();
      if (data.error) { showToast(`Error: ${data.error}`, 'error'); return; }
      if (data.text) {
        insertTextIntoChat(data.text);
        showToast(`✓ "${data.text.substring(0, 50)}${data.text.length > 50 ? '...' : ''}"`, 'success');
      } else {
        showToast('No speech detected', 'warn');
      }
    } catch (err) {
      showToast('Voice server unreachable', 'error');
    } finally {
      clearProcessingState();
    }
  }

  // ── Chat Input Injection ──────────────────────────────────────────────
  function insertTextIntoChat(text) {
    const root = document.querySelector('openclaw-app');
    if (!root) return;
    function findInput(el) {
      if (!el) return null;
      const shadow = el.shadowRoot || el;
      const candidates = shadow.querySelectorAll('textarea, input[type="text"], [contenteditable="true"]');
      for (const c of candidates) { if (c.offsetParent !== null) return c; }
      for (const child of shadow.querySelectorAll('*')) {
        if (child.shadowRoot) { const found = findInput(child); if (found) return found; }
      }
      return null;
    }
    const input = findInput(root);
    if (input) {
      // Set value without triggering auto-submit events
      const nativeSet = Object.getOwnPropertyDescriptor(
        input.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype, 'value'
      )?.set;
      if (nativeSet) nativeSet.call(input, text); else input.value = text;
      // Only trigger input event for UI updates, not change (which can trigger submit)
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.focus();
    } else {
      navigator.clipboard.writeText(text).then(() => showToast('Copied to clipboard — paste into chat', 'info'));
    }
  }

  // ── Toast ─────────────────────────────────────────────────────────────
  function showToast(msg, type = 'info') {
    const toast = document.createElement('div');
    const colors = { info: '#3498db', success: '#2ecc71', error: '#e74c3c', warn: '#f39c12' };
    Object.assign(toast.style, {
      position: 'fixed', bottom: '240px', right: '24px', zIndex: '10001',
      padding: '8px 16px', borderRadius: '8px', background: colors[type] || colors.info,
      color: '#fff', fontSize: '13px', maxWidth: '300px',
      boxShadow: '0 2px 8px rgba(0,0,0,0.3)', transition: 'opacity 0.3s', opacity: '1',
    });
    toast.textContent = msg;
    document.body.appendChild(toast);
    setTimeout(() => { toast.style.opacity = '0'; setTimeout(() => toast.remove(), 300); }, 3000);
  }

  // ── Styles ────────────────────────────────────────────────────────────
  function addStyles() {
    const style = document.createElement('style');
    style.textContent = `
      @keyframes voice-io-pulse {
        0% { box-shadow: 0 0 0 0 rgba(231, 76, 60, 0.7); }
        70% { box-shadow: 0 0 0 12px rgba(231, 76, 60, 0); }
        100% { box-shadow: 0 0 0 0 rgba(231, 76, 60, 0); }
      }
      @keyframes voice-io-wave {
        0% { box-shadow: 0 0 0 0 rgba(46, 204, 113, 0.7); }
        50% { box-shadow: 0 0 0 8px rgba(46, 204, 113, 0); }
        100% { box-shadow: 0 0 0 0 rgba(46, 204, 113, 0); }
      }
    `;
    document.head.appendChild(style);
  }

  // ── Keyboard Shortcuts ────────────────────────────────────────────────
  document.addEventListener('keydown', (e) => {
    if (e.altKey && e.key === 'm') { e.preventDefault(); toggleRecording(); }      // Alt+M = dictate
    if (e.altKey && e.key === 'c') { e.preventDefault(); toggleConversation(); }   // Alt+C = conversation
  });

  // ── Init ──────────────────────────────────────────────────────────────
  function init() {
    if (document.getElementById('voice-io-mic')) return;
    addStyles();
    micButton = createMicButton();
    convoButton = createConvoButton();
    document.body.appendChild(micButton);
    document.body.appendChild(convoButton);
    console.log('[voice-io] Buttons injected. Alt+M=dictate, Alt+C=conversation');

    // Check if conversation is already running
    fetch(`${VOICE_SERVER}/conversation/status`)
      .then(r => r.json())
      .then(d => {
        if (d.running) { convoActive = true; setConvoButtonState(true); }
        console.log('[voice-io] Server:', d);
      })
      .catch(() => console.warn('[voice-io] Voice server not running'));
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
