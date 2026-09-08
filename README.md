# VoiceBot OS — Multimodal Voice Assistant & Gesture Console (PWA)

A clean, robust, full-stack voice assistant and gesture control console. Features **Tailwind CSS UI/UX**, **Progressive Web App (PWA)** installability, **MediaPipe Hand Landmarker** OS cursor control, **Google Gemini 3.6/2.5 Flash** intelligence, and cross-platform hardware control for volume and display brightness.

---

## 🚀 Key Capabilities

- 📱 **Progressive Web App (PWA)**: Installable directly on desktop, tablet, and mobile devices (`display: standalone`, offline caching service worker, app manifest, custom icons).
- 🎙️ **Multimodal Voice Control**:
  - **In-Browser Web Speech API**: Instant zero-latency speech recognition directly inside the PWA on any device.
  - **Host Microphone Engine**: Background speech recognition via `sounddevice` / `speech_recognition`.
  - **Natural Command Parsing**: Supports volume up/down, mute/unmute, brightness up/down, exact percentage setting (e.g. *"volume 70%"*, *"brightness 40"*), desktop cursor toggles, and web search.
  - **Text-to-Speech (TTS)**: Reads out answers and action confirmations.
- 🖐️ **Hand Tracking & Cursor Control**:
  - **MediaPipe HandLandmarker**: 21 3D hand landmarks processed in real-time.
  - **Smoothed Cursor**: Exponential moving average (EMA) jitter reduction and deadzone filtering for accurate cursor navigation.
  - **Pinch-to-Click**: Distance tracking between index finger and thumb triggers hardware mouse clicks.
  - **Middle Finger Scroll**: Vertical movement of middle finger triggers smooth page scrolling.
  - **UI Toggle**: Easily switch between "View Only" HUD tracking and "Desktop OS Cursor Control".
- 🔊 **System Volume & Brightness Control**:
  - Native Linux (`pactl`, `amixer`, `brightnessctl`, `xbacklight`), macOS (`osascript`), and Windows support.
  - Granular adjustments (-5% / +5%), exact percentage sliders, mute toggle, and quick presets.
- 🧠 **Gemini Search & Assistant**:
  - Powered by Google Gemini (`gemini-3.6-flash`, `gemini-2.5-flash`).
  - Search history, copy-to-clipboard, speech playback, and graceful offline fallback.
- 🎨 **Modern Tailwind UI/UX (No AI Slop)**:
  - Deep obsidian dark theme (`zinc-950`), subtle borders, backdrop blurs, tactile range sliders, and dynamic telemetry HUD.

---

## 📂 Project Structure

```
Test2/
├── .env.example              # Environment variables template
├── .gitignore
├── requirements.txt          # Production dependencies
├── README.md                 # Project documentation
├── AGENTS.md                 # Agent architecture & guidelines
├── main.py                   # Server entry point & graceful shutdown
├── hand_landmarker.task      # MediaPipe HandLandmarker model asset
├── config/
│   ├── __init__.py           # Config package exports
│   └── settings.py           # Centralized type-safe settings
├── src/
│   ├── __init__.py           # Core exports
│   ├── core/
│   │   ├── __init__.py
│   │   └── logger.py         # Thread-safe ring buffer activity logger
│   ├── services/
│   │   ├── __init__.py
│   │   ├── system_service.py # Cross-platform volume & brightness controller
│   │   ├── voice_service.py  # Voice recognition & natural language parsing
│   │   ├── vision_service.py # MediaPipe hand tracking & cursor controller
│   │   └── search_service.py # Gemini LLM integration with model fallbacks
│   ├── web/
│   │   ├── __init__.py
│   │   ├── app.py            # Flask application factory
│   │   ├── routes.py         # REST API endpoints & PWA routes
│   │   └── camera_stream.py  # Low-latency camera MJPEG stream manager
│   ├── system_control.py     # Backward-compatible shim -> services.system_service
│   ├── voice_handler.py      # Backward-compatible shim -> services.voice_service
│   ├── hand_tracker.py       # Backward-compatible shim -> services.vision_service
│   ├── web_search.py         # Backward-compatible shim -> services.search_service
│   └── web_app.py            # Backward-compatible shim -> web.app
├── static/
│   ├── manifest.json         # PWA Web App Manifest
│   ├── sw.js                 # PWA Service Worker (offline shell & cache bypass)
│   ├── icons/                # High-res PWA & favicon assets
│   ├── css/
│   │   └── custom.css        # Range slider thumbs & voice wave animations
│   └── js/
│       └── app.js            # PWA controller, Web Speech API, and UI state
├── templates/
│   └── index.html            # Tailwind-styled responsive dashboard
└── tests/
    ├── __init__.py
    ├── test_config.py        # Config unit tests
    ├── test_system_service.py# Volume & brightness logic tests
    ├── test_voice_service.py # Voice command parser tests
    ├── test_vision_service.py# Hand tracking tests
    ├── test_search_service.py# Gemini search tests
    └── test_web_routes.py    # Flask REST API & PWA routes tests
```

---

## 🛠️ Setup & Installation

### 1. Create Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or: .venv\Scripts\activate on Windows
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables
```bash
cp .env.example .env
# Edit .env and set your GEMINI_API_KEY
```

### 4. Run the Application
```bash
python main.py
```
Open your browser at **`http://localhost:5000`**. On supported browsers (Chrome, Edge, Safari, Android Chrome), click **"Install App"** in the top navigation bar to install VoiceBot as a native standalone application.

---

## 🧪 Running Unit Tests

Run the full pytest suite:
```bash
.venv/bin/pytest -v
```
All 34 unit tests verify system controls, voice command extraction, vision gestures, search services, and web API endpoints.

---

## 🗣️ Voice Commands Cheatsheet

| Voice Command | Action |
|---------------|--------|
| *"volume up"* / *"louder"* / *"boost volume"* | Increase volume by step (default 5%) |
| *"volume down"* / *"quieter"* / *"lower volume"* | Decrease volume by step (default 5%) |
| *"volume 75%"* / *"set volume to 40"* | Jump volume to exact percentage (0-100%) |
| *"mute"* / *"silence"* | Mute system output audio |
| *"unmute"* / *"sound on"* | Unmute system audio |
| *"brightness up"* / *"brighter"* | Increase display brightness by step |
| *"brightness down"* / *"dimmer"* | Decrease display brightness by step |
| *"brightness 80%"* / *"set brightness to 50"* | Jump screen brightness to exact percentage |
| *"toggle cursor"* / *"mouse on"* / *"mouse off"* | Toggle whether hand moves OS mouse pointer |
| *"search \<query\>"* / *"google \<query\>"* | Query Google Gemini with live answer |
| *"what is \<topic\>"* / *"who is \<name\>"* | Direct question to Gemini assistant |

---

## 🖐️ Hand Gestures Cheatsheet

| Hand Gesture | Function |
|--------------|----------|
| **Index Fingertip** | Move OS cursor smoothly across desktop screen |
| **Pinch (Thumb + Index)** | Left click with visual reticle confirmation |
| **Middle Finger Raised** | Scroll up page |
| **Middle Finger Lowered** | Scroll down page |

---

## 📡 REST API Endpoints

- `GET /` — Responsive Tailwind PWA dashboard
- `GET /manifest.json` — PWA Web App Manifest
- `GET /sw.js` — PWA Service Worker
- `GET /video_feed` — Real-time MJPEG camera stream with HUD
- `GET /api/status` — Hardware telemetry (volume, brightness, camera, cursor, mic)
- `POST /api/volume` — Set volume `{ "level": 0-100 }`
- `POST /api/volume/up` & `/api/volume/down` — Step volume up / down
- `POST /api/volume/toggle-mute`, `/api/mute`, `/api/unmute` — Mute controls
- `POST /api/brightness` — Set brightness `{ "level": 0-100 }`
- `POST /api/brightness/up` & `/api/brightness/down` — Step brightness up / down
- `POST /api/voice/command` — Execute speech text `{ "text": "volume 75" }`
- `POST /api/voice/listen` — Listen once via server microphone
- `POST /api/voice/toggle` — Toggle continuous host microphone listener
- `POST /api/camera/cursor_control` — Enable / disable desktop cursor tracking
- `POST /api/camera/toggle` — Start / pause webcam feed
- `POST /api/search` — Gemini search inquiry `{ "query": "..." }`
- `GET /api/search/history` & `POST /api/search/clear` — Search history management
- `GET /api/logs` & `POST /api/logs/clear` — Activity logs
