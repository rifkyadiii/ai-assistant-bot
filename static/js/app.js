/**
 * VoiceBot OS - Client Application Logic
 * PWA lifecycle, Web Speech API voice assistant, real-time hardware telemetry,
 * gesture telemetry, and Gemini search integration.
 */

// ==========================================
// Application State
// ==========================================
const state = {
  volume: 50,
  muted: false,
  brightness: 50,
  cameraActive: true,
  cursorEnabled: false,
  cursorAvailable: false,
  voiceListening: false,
  isRecordingWebSpeech: false,
  deferredInstallPrompt: null,
  isStandalone: false,
  lastGesture: 'NO_HAND'
};

// ==========================================
// PWA Service Worker & Install Handler
// ==========================================
function initPWA() {
  // Check if running in standalone mode
  const isStandalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
  state.isStandalone = isStandalone;

  const pwaBadge = document.getElementById('pwaModeBadge');
  const installBtn = document.getElementById('installAppBtn');

  if (isStandalone) {
    if (pwaBadge) pwaBadge.classList.remove('hidden');
    if (installBtn) installBtn.classList.add('hidden');
  }

  // Register service worker
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js')
      .then((reg) => {
        console.log('[PWA] Service Worker registered with scope:', reg.scope);
      })
      .catch((err) => {
        console.warn('[PWA] Service Worker registration failed:', err);
      });
  }

  // Handle native install prompt
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    state.deferredInstallPrompt = e;
    if (installBtn && !state.isStandalone) {
      installBtn.classList.remove('hidden');
    }
  });

  window.addEventListener('appinstalled', () => {
    state.deferredInstallPrompt = null;
    if (installBtn) installBtn.classList.add('hidden');
    if (pwaBadge) pwaBadge.classList.remove('hidden');
    showToast('VoiceBot installed as native app!', 'success');
  });
}

async function triggerInstallPrompt() {
  if (!state.deferredInstallPrompt) {
    showToast('To install, use browser menu: Add to Home Screen / Install App', 'info');
    return;
  }
  state.deferredInstallPrompt.prompt();
  const { outcome } = await state.deferredInstallPrompt.userChoice;
  if (outcome === 'accepted') {
    state.deferredInstallPrompt = null;
    const installBtn = document.getElementById('installAppBtn');
    if (installBtn) installBtn.classList.add('hidden');
  }
}

// ==========================================
// Toast Notification System
// ==========================================
function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const toast = document.createElement('div');
  const colors = {
    success: 'bg-emerald-950/90 border-emerald-500/40 text-emerald-200',
    warning: 'bg-amber-950/90 border-amber-500/40 text-amber-200',
    error: 'bg-rose-950/90 border-rose-500/40 text-rose-200',
    info: 'bg-zinc-900/90 border-zinc-700/60 text-zinc-200'
  };

  toast.className = `flex items-center gap-2 px-4 py-2.5 rounded-lg border text-xs font-medium shadow-xl backdrop-blur-md transition-all duration-300 transform translate-y-2 opacity-0 ${colors[type] || colors.info}`;
  toast.innerHTML = `
    <span class="w-2 h-2 rounded-full ${type === 'success' ? 'bg-emerald-400' : (type === 'error' ? 'bg-rose-400' : 'bg-cyan-400')}"></span>
    <span>${escapeHtml(message)}</span>
  `;

  container.appendChild(toast);
  requestAnimationFrame(() => {
    toast.classList.remove('translate-y-2', 'opacity-0');
  });

  setTimeout(() => {
    toast.classList.add('opacity-0', 'translate-y-2');
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/[&<>'"]/g, 
    tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
  );
}

// ==========================================
// API Communication Helpers
// ==========================================
async function apiFetch(url, method = 'GET', body = null) {
  try {
    const opts = {
      method,
      headers: { 'Content-Type': 'application/json' },
    };
    if (body && method !== 'GET') {
      opts.body = JSON.stringify(body);
    }
    const res = await fetch(url, opts);
    return await res.json();
  } catch (err) {
    console.error(`API Error [${method} ${url}]:`, err);
    return null;
  }
}

// ==========================================
// Hardware & Status Telemetry
// ==========================================
async function refreshStatus() {
  const data = await apiFetch('/api/status');
  if (!data || !data.ok) {
    updateOnlineBadge(false);
    return;
  }

  updateOnlineBadge(true);

  // Update volume & brightness
  state.volume = data.volume;
  state.muted = data.muted;
  state.brightness = data.brightness;
  state.cameraActive = data.camera_active;
  state.cursorEnabled = data.cursor_enabled;
  state.cursorAvailable = data.cursor_available;
  state.voiceListening = data.voice_listening;

  renderVolumeUI();
  renderBrightnessUI();
  renderCameraUI(data.gesture_telemetry);
  renderVoiceStateUI();
}

function updateOnlineBadge(isOnline) {
  const dot = document.getElementById('connectionDot');
  const text = document.getElementById('connectionText');
  if (isOnline) {
    if (dot) dot.className = 'w-2 h-2 rounded-full bg-emerald-500 animate-pulse';
    if (text) text.textContent = 'System Online';
  } else {
    if (dot) dot.className = 'w-2 h-2 rounded-full bg-rose-500';
    if (text) text.textContent = 'Connecting...';
  }
}

// ==========================================
// Volume Controls
// ==========================================
let volDebounce = null;

function renderVolumeUI() {
  const valElem = document.getElementById('volumeValue');
  const slider = document.getElementById('volumeSlider');
  const muteBtn = document.getElementById('muteToggleBtn');
  const muteText = document.getElementById('muteBtnText');
  const volIcon = document.getElementById('volumeIcon');

  if (valElem) valElem.textContent = `${state.volume}%`;
  if (slider && document.activeElement !== slider) slider.value = state.volume;

  if (muteBtn && muteText) {
    if (state.muted) {
      muteBtn.className = 'px-3 py-1.5 rounded-lg text-xs font-semibold bg-rose-950/80 border border-rose-600/50 text-rose-300 hover:bg-rose-900 transition-colors';
      muteText.textContent = 'Muted';
    } else {
      muteBtn.className = 'px-3 py-1.5 rounded-lg text-xs font-semibold bg-zinc-800/80 border border-zinc-700/60 text-zinc-300 hover:bg-zinc-700 transition-colors';
      muteText.textContent = 'Mute';
    }
  }

  // Icon state
  if (volIcon) {
    if (state.muted || state.volume === 0) {
      volIcon.innerHTML = `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 4.663 12 5.109 12 6v12c0 .891-1.077 1.337-1.707.707L5.586 15z M17 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2" />`;
    } else {
      volIcon.innerHTML = `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 4.663 12 5.109 12 6v12c0 .891-1.077 1.337-1.707.707L5.586 15z" />`;
    }
  }
}

function handleVolumeSlider(val) {
  const level = parseInt(val, 10);
  state.volume = level;
  renderVolumeUI();

  clearTimeout(volDebounce);
  volDebounce = setTimeout(async () => {
    const res = await apiFetch('/api/volume', 'POST', { level });
    if (res && res.ok) {
      state.muted = res.muted;
      renderVolumeUI();
    }
  }, 120);
}

async function adjustVolumeStep(step) {
  const endpoint = step > 0 ? '/api/volume/up' : '/api/volume/down';
  const res = await apiFetch(endpoint, 'POST');
  if (res && res.ok) {
    state.volume = res.volume;
    state.muted = res.muted;
    renderVolumeUI();
    showToast(`Volume ${step > 0 ? 'increased' : 'decreased'} to ${res.volume}%`);
  }
}

async function toggleMute() {
  const res = await apiFetch('/api/volume/toggle-mute', 'POST');
  if (res && res.ok) {
    state.muted = res.muted;
    renderVolumeUI();
    showToast(res.muted ? 'Audio Muted' : 'Audio Unmuted', res.muted ? 'warning' : 'success');
  }
}

// ==========================================
// Brightness Controls
// ==========================================
let briDebounce = null;

function renderBrightnessUI() {
  const valElem = document.getElementById('brightnessValue');
  const slider = document.getElementById('brightnessSlider');
  if (valElem) valElem.textContent = `${state.brightness}%`;
  if (slider && document.activeElement !== slider) slider.value = state.brightness;
}

function handleBrightnessSlider(val) {
  const level = parseInt(val, 10);
  state.brightness = level;
  renderBrightnessUI();

  clearTimeout(briDebounce);
  briDebounce = setTimeout(async () => {
    const res = await apiFetch('/api/brightness', 'POST', { level });
    if (res && res.ok) {
      state.brightness = res.brightness;
      renderBrightnessUI();
    }
  }, 120);
}

async function adjustBrightnessStep(step) {
  const endpoint = step > 0 ? '/api/brightness/up' : '/api/brightness/down';
  const res = await apiFetch(endpoint, 'POST');
  if (res && res.ok) {
    state.brightness = res.brightness;
    renderBrightnessUI();
    showToast(`Brightness ${step > 0 ? 'increased' : 'decreased'} to ${res.brightness}%`);
  }
}

// ==========================================
// Camera & Hand Gesture Controls
// ==========================================
function renderCameraUI(telemetry) {
  const cursorToggle = document.getElementById('cursorControlToggle');
  const cursorPill = document.getElementById('cursorStatusPill');
  const gestureBadge = document.getElementById('gesturePill');

  if (cursorToggle) {
    cursorToggle.checked = state.cursorEnabled;
  }

  if (cursorPill) {
    if (state.cursorEnabled) {
      cursorPill.className = 'px-2.5 py-1 rounded-full text-[11px] font-semibold bg-emerald-950/80 border border-emerald-500/50 text-emerald-300';
      cursorPill.textContent = 'Cursor Control: ACTIVE';
    } else {
      cursorPill.className = 'px-2.5 py-1 rounded-full text-[11px] font-semibold bg-zinc-800/80 border border-zinc-700/60 text-zinc-400';
      cursorPill.textContent = 'Cursor: VIEW ONLY';
    }
  }

  if (telemetry && gestureBadge) {
    const g = telemetry.gesture || 'NO_HAND';
    state.lastGesture = g;

    const gestureStyles = {
      'POINTER': { text: 'Pointer Tracking', bg: 'bg-cyan-950/80 border-cyan-500/50 text-cyan-300' },
      'PINCH_CLICK': { text: 'Pinch: Left Click', bg: 'bg-emerald-950/90 border-emerald-400/80 text-emerald-200 animate-pulse' },
      'SCROLL_UP': { text: 'Scroll Up', bg: 'bg-blue-950/80 border-blue-500/50 text-blue-300' },
      'SCROLL_DOWN': { text: 'Scroll Down', bg: 'bg-blue-950/80 border-blue-500/50 text-blue-300' },
      'NO_HAND': { text: 'Searching Hand...', bg: 'bg-zinc-900/80 border-zinc-700/50 text-zinc-400' }
    };

    const style = gestureStyles[g] || gestureStyles['NO_HAND'];
    gestureBadge.className = `px-3 py-1 rounded-full text-xs font-semibold border backdrop-blur-md transition-all ${style.bg}`;
    gestureBadge.textContent = style.text;
  }
}

async function toggleDesktopCursorControl() {
  const res = await apiFetch('/api/camera/cursor_control', 'POST');
  if (res && res.ok) {
    state.cursorEnabled = res.cursor_enabled;
    renderCameraUI();
    showToast(
      state.cursorEnabled ? 'Desktop cursor control activated' : 'Desktop cursor control paused',
      state.cursorEnabled ? 'success' : 'info'
    );
  }
}

async function toggleCameraFeed() {
  const res = await apiFetch('/api/camera/toggle', 'POST');
  if (res && res.ok) {
    state.cameraActive = res.camera_active;
    const feed = document.getElementById('cameraVideoFeed');
    if (feed) {
      if (state.cameraActive) {
        feed.src = '/video_feed?' + Date.now();
        showToast('Camera feed resumed', 'success');
      } else {
        feed.src = '';
        showToast('Camera feed paused', 'info');
      }
    }
  }
}

// ==========================================
// Interactive Voice Assistant (Web Speech + Backend API)
// ==========================================
let speechRecognition = null;

function initWebSpeech() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    console.log('[Voice] Web Speech API not supported in this browser. Backend mic fallback available.');
    return;
  }

  speechRecognition = new SpeechRecognition();
  speechRecognition.continuous = false;
  speechRecognition.interimResults = true;
  speechRecognition.lang = 'en-US';

  const transcriptBox = document.getElementById('voiceTranscriptText');
  const statusLabel = document.getElementById('voiceStatusLabel');

  speechRecognition.onstart = () => {
    state.isRecordingWebSpeech = true;
    setOrbState('listening');
    if (statusLabel) statusLabel.textContent = 'Listening... Speak your command';
    if (transcriptBox) transcriptBox.textContent = 'Listening...';
  };

  speechRecognition.onresult = (event) => {
    let interim = '';
    let final = '';

    for (let i = event.resultIndex; i < event.results.length; ++i) {
      if (event.results[i].isFinal) {
        final += event.results[i][0].transcript;
      } else {
        interim += event.results[i][0].transcript;
      }
    }

    if (transcriptBox) {
      transcriptBox.textContent = final || interim || 'Listening...';
    }

    if (final) {
      setOrbState('processing');
      executeVoiceCommand(final.trim());
    }
  };

  speechRecognition.onerror = (event) => {
    console.warn('[Voice] Speech recognition error:', event.error);
    if (statusLabel) statusLabel.textContent = `Recognition idle (${event.error})`;
    stopWebSpeech();
  };

  speechRecognition.onend = () => {
    stopWebSpeech();
  };
}

function toggleWebSpeech() {
  if (!speechRecognition) {
    // Fallback to server microphone listen
    triggerServerMicListen();
    return;
  }

  if (state.isRecordingWebSpeech) {
    speechRecognition.stop();
  } else {
    try {
      speechRecognition.start();
    } catch (e) {
      console.warn('Recognition start issue:', e);
      stopWebSpeech();
    }
  }
}

function stopWebSpeech() {
  state.isRecordingWebSpeech = false;
  const statusLabel = document.getElementById('voiceStatusLabel');

  if (orbState === 'listening') setOrbState('idle');
  if (statusLabel) statusLabel.textContent = 'Tap the orb to speak';
}

async function triggerServerMicListen() {
  const statusLabel = document.getElementById('voiceStatusLabel');
  const transcriptBox = document.getElementById('voiceTranscriptText');
  setOrbState('listening');
  if (statusLabel) statusLabel.textContent = 'Server mic listening for 4 seconds...';
  if (transcriptBox) transcriptBox.textContent = 'Listening on host microphone...';

  const res = await apiFetch('/api/voice/listen', 'POST');
  setOrbState('processing');
  if (res && res.ok) {
    if (transcriptBox) transcriptBox.textContent = res.raw_text || res.message;
    handleVoiceCommandResult(res);
  } else {
    const err = res?.error || 'No speech detected';
    if (transcriptBox) transcriptBox.textContent = `(${err})`;
    showToast(err, 'warning');
    setOrbState('idle');
  }
  if (statusLabel) statusLabel.textContent = 'Tap the orb to speak';
}

async function executeVoiceCommand(text) {
  const transcriptBox = document.getElementById('voiceTranscriptText');
  const statusLabel = document.getElementById('voiceStatusLabel');
  if (statusLabel) statusLabel.textContent = 'Processing command...';

  const res = await apiFetch('/api/voice/command', 'POST', { text });
  if (res) {
    handleVoiceCommandResult(res);
  }
  if (statusLabel) statusLabel.textContent = 'Tap the orb to speak';
}

function handleVoiceCommandResult(res) {
  const resultBanner = document.getElementById('voiceResultBanner');
  const resultMsg = document.getElementById('voiceResultMsg');

  if (resultBanner && resultMsg) {
    resultMsg.textContent = res.message || res.speech;
    resultBanner.classList.remove('hidden');
    setTimeout(() => resultBanner.classList.add('hidden'), 5000);
  }

  // If search was executed, populate search response
  if (res.search_result && res.search_result.response) {
    displaySearchResponse(res.search_result.query, res.search_result.response, res.search_result.source);
  }

  // Voice synthesis feedback if available
  if (res.speech && 'speechSynthesis' in window) {
    speakText(res.speech);
  } else {
    flashOrbSuccess();
  }

  // Refresh system sliders
  refreshStatus();
  refreshLogs();
}

function speakText(text) {
  try {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    // Select a natural human-sounding voice if available
    const voices = window.speechSynthesis.getVoices();
    if (voices && voices.length) {
      const preferred = pickNaturalVoice(voices);
      if (preferred) utterance.voice = preferred;
    }
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.onend = () => setOrbState('success');
    utterance.onerror = () => setOrbState('idle');
    window.speechSynthesis.speak(utterance);
    setOrbState('speaking');
  } catch (err) {
    console.warn('Speech synthesis error:', err);
    setOrbState('success');
  }
}

function pickNaturalVoice(voices) {
  const priority = [
    { lang: 'en-US', name: /(natural|neural|online|premium|enhanced)/i },
    { lang: 'en-GB', name: /(natural|neural|online|premium|enhanced)/i },
    { lang: 'en-US', name: /samantha|ava|aria|jenny|libby/i },
    { lang: 'en', name: /priya|samantha|zira|hazel|clara/i }
  ];
  for (const pref of priority) {
    const match = voices.find(v =>
      (v.lang.startsWith(pref.lang)) &&
      (!pref.name || pref.name.test(v.name))
    );
    if (match) return match;
  }
  // Fallback to a female-sounding natural voice
  return voices.find(v => /female|woman|samantha|aria|jenny/i.test(v.name)) || null;
}

// ==========================================
// Fluid Orb — Interactive Voice Assistant
// ==========================================

let orbState = 'idle';
let orbWaveAnim = null;

function setOrbState(state) {
  orbState = state;
  const container = document.getElementById('orbContainer');
  const statusText = document.getElementById('orbStatusText');
  if (!container) return;

  container.classList.remove('orb-listening', 'orb-processing', 'orb-speaking', 'orb-success');
  container.classList.add(`orb-${state}`);

  if (statusText) {
    const labels = {
      idle: 'Ready',
      listening: 'Listening...',
      processing: 'Thinking...',
      speaking: 'Speaking',
      success: 'Done!'
    };
    statusText.textContent = labels[state] || 'Ready';
  }

  startOrbWaveform(state === 'listening' || state === 'speaking');
}

function toggleOrbInteraction() {
  if (orbState === 'listening') {
    stopWebSpeech();
    setOrbState('idle');
    return;
  }
  triggerParticleBurst();
  toggleWebSpeech();
}

function triggerParticleBurst() {
  const container = document.getElementById('orbContainer');
  if (!container) return;
  for (let i = 0; i < 6; i++) {
    const ripple = document.createElement('div');
    ripple.className = 'orb-ripple';
    ripple.style.top = '50%';
    ripple.style.left = '50%';
    container.appendChild(ripple);
    setTimeout(() => ripple.remove(), 1000);
  }
}

function startOrbWaveform(active) {
  const canvas = document.getElementById('orbWaveform');
  if (!canvas) return;

  if (active && !orbWaveAnim) {
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    let frame = 0;

    orbWaveAnim = setInterval(() => {
      ctx.clearRect(0, 0, width, height);
      const bars = 20;
      const barW = width / bars;
      for (let i = 0; i < bars; i++) {
        const base = Math.sin(frame * 0.2 + i * 0.6) * 0.5 + 0.5;
        const vibrate = Math.sin(frame * 0.5 + i * 0.3) * 0.2;
        const barH = 6 + base * 24 + vibrate * 10;
        const color = orbState === 'listening' ? 'rgba(239,68,68,0.7)' : 'rgba(168,85,247,0.7)';
        ctx.fillStyle = color;
        ctx.fillRect(i * barW + barW * 0.2, (height - barH) / 2, barW * 0.6, barH);
      }
      frame++;
    }, 40);
  } else if (!active && orbWaveAnim) {
    clearInterval(orbWaveAnim);
    orbWaveAnim = null;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  }
}

function flashOrbSuccess() {
  setOrbState('success');
  setTimeout(() => setOrbState('idle'), 1400);
}

// ==========================================
// Desktop Control Actions
// ==========================================

async function desktopAction(action, payload = {}) {
  const res = await apiFetch('/api/desktop/action', 'POST', { action, payload });
  if (res && res.ok) {
    showToast(res.message || 'Action executed', 'success');
    if (res.path) showToast('Saved: ' + res.path, 'info');
  } else {
    showToast(res?.error || res?.message || 'Action failed', 'error');
  }
  refreshLogs();
}

function renderVoiceStateUI() {
  const serverMicPill = document.getElementById('serverVoiceStatusPill');
  if (serverMicPill) {
    if (state.voiceListening) {
      serverMicPill.className = 'px-2.5 py-1 rounded-full text-[11px] font-semibold bg-emerald-950/80 border border-emerald-500/50 text-emerald-300';
      serverMicPill.textContent = 'Server Mic: LISTENING';
    } else {
      serverMicPill.className = 'px-2.5 py-1 rounded-full text-[11px] font-semibold bg-zinc-800/80 border border-zinc-700/60 text-zinc-400';
      serverMicPill.textContent = 'Server Mic: IDLE';
    }
  }
}

async function toggleServerVoiceListener() {
  const res = await apiFetch('/api/voice/toggle', 'POST');
  if (res && res.ok) {
    state.voiceListening = res.listening;
    renderVoiceStateUI();
    showToast(
      res.listening ? 'Server background voice listener active' : 'Server voice listener stopped',
      res.listening ? 'success' : 'info'
    );
  }
}

// ==========================================
// Gemini Search & Intelligence
// ==========================================
async function doGeminiSearch(customQuery = null) {
  const input = document.getElementById('searchInput');
  const query = (customQuery || (input ? input.value : '')).trim();
  if (!query) return;

  const searchBtn = document.getElementById('searchSubmitBtn');
  const spinner = document.getElementById('searchSpinner');
  const btnText = document.getElementById('searchBtnText');

  if (searchBtn) searchBtn.disabled = true;
  if (spinner) spinner.classList.remove('hidden');
  if (btnText) btnText.textContent = 'Thinking...';

  const res = await apiFetch('/api/search', 'POST', { query });

  if (searchBtn) searchBtn.disabled = false;
  if (spinner) spinner.classList.add('hidden');
  if (btnText) btnText.textContent = 'Search';

  if (res && res.ok && res.result) {
    displaySearchResponse(res.result.query, res.result.response, res.result.source);
    loadSearchHistory();
  } else {
    displaySearchResponse(query, res?.error || 'Failed to retrieve response', 'error');
  }

  if (input && !customQuery) input.value = '';
}

function displaySearchResponse(query, responseText, source) {
  const container = document.getElementById('searchResponseCard');
  const queryElem = document.getElementById('searchResponseQuery');
  const textElem = document.getElementById('searchResponseText');
  const sourceBadge = document.getElementById('searchResponseSource');

  if (container) container.classList.remove('hidden');
  if (queryElem) queryElem.textContent = `"${query}"`;
  if (textElem) textElem.textContent = responseText;
  if (sourceBadge) {
    sourceBadge.textContent = source || 'Gemini';
  }
}

function copySearchResponse() {
  const textElem = document.getElementById('searchResponseText');
  if (!textElem) return;
  navigator.clipboard.writeText(textElem.textContent).then(() => {
    showToast('Response copied to clipboard', 'success');
  });
}

function speakSearchResponse() {
  const textElem = document.getElementById('searchResponseText');
  if (!textElem) return;
  speakText(textElem.textContent.slice(0, 300));
}

async function loadSearchHistory() {
  const res = await apiFetch('/api/search/history');
  const container = document.getElementById('searchHistoryChips');
  if (!container || !res || !res.results) return;

  if (res.results.length === 0) {
    container.innerHTML = `<span class="text-xs text-zinc-500">No recent queries</span>`;
    return;
  }

  container.innerHTML = res.results.slice(0, 6).map(item => `
    <button onclick="doGeminiSearch('${escapeHtml(item.query).replace(/'/g, "\\'")}')" 
      class="px-2.5 py-1 rounded-full text-xs bg-zinc-800/90 border border-zinc-700/60 text-zinc-300 hover:text-cyan-300 hover:border-cyan-500/50 transition-colors truncate max-w-[200px]">
      ${escapeHtml(item.query)}
    </button>
  `).join('');
}

// ==========================================
// Activity & System Logs
// ==========================================
async function refreshLogs() {
  const res = await apiFetch('/api/logs?limit=40');
  const logBox = document.getElementById('activityLogBox');
  if (!logBox || !res || !res.entries) return;

  logBox.innerHTML = res.entries.map(entry => {
    const categoryColors = {
      'SYS': 'bg-sky-950/80 text-sky-300 border-sky-600/40',
      'VOICE': 'bg-purple-950/80 text-purple-300 border-purple-600/40',
      'GESTURE': 'bg-emerald-950/80 text-emerald-300 border-emerald-600/40',
      'SEARCH': 'bg-amber-950/80 text-amber-300 border-amber-600/40',
      'ERROR': 'bg-rose-950/80 text-rose-300 border-rose-600/40'
    };
    const catStyle = categoryColors[entry.category] || 'bg-zinc-800 text-zinc-300 border-zinc-700';

    return `
      <div class="flex items-start gap-2 py-0.5 text-[11px] font-mono leading-relaxed">
        <span class="text-zinc-500 select-none">${entry.time}</span>
        <span class="px-1.5 py-0.2 rounded border text-[10px] font-semibold tracking-wider ${catStyle}">${entry.category}</span>
        <span class="text-zinc-300 break-words flex-1">${escapeHtml(entry.message)}</span>
      </div>
    `;
  }).join('');

  logBox.scrollTop = logBox.scrollHeight;
}

async function clearLogs() {
  await apiFetch('/api/logs/clear', 'POST');
  refreshLogs();
  showToast('Logs cleared', 'info');
}

// ==========================================
// Initialization
// ==========================================
document.addEventListener('DOMContentLoaded', () => {
  initPWA();
  initWebSpeech();
  refreshStatus();
  refreshLogs();
  loadSearchHistory();

  // Initialize orb to idle and preload available TTS voices
  setOrbState('idle');
  if ('speechSynthesis' in window) {
    speechSynthesis.getVoices();
    speechSynthesis.onvoiceschanged = () => speechSynthesis.getVoices();
  }

  // Orb keyboard accessibility (Enter / Space activates)
  const orb = document.getElementById('orbContainer');
  if (orb) {
    orb.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        toggleOrbInteraction();
      }
    });
  }

  // Search enter key listener
  const searchInput = document.getElementById('searchInput');
  if (searchInput) {
    searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') doGeminiSearch();
    });
  }

  // Periodic polling for telemetry and logs
  setInterval(refreshStatus, 2500);
  setInterval(refreshLogs, 3000);
});
