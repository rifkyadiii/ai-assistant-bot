# AGENTS.md

## Project Overview
Interactive multimodal Python voicebot and Progressive Web App (PWA) with voice commands, MediaPipe hand tracking for OS cursor control, and Google Gemini LLM web search. Controls system volume and brightness, performs natural language searches with voice response readout, provides gesture-based cursor interaction, and serves a modern Tailwind CSS PWA interface installable as a native app on mobile and desktop devices.

## Tech Stack
- Python 3.9+ / 3.14
- **SpeechRecognition & SoundDevice** - Multi-backend speech recognition (in-browser Web Speech API + server microphone)
- **MediaPipe** - Hand landmark detection for cursor control (v1.0 tasks API with `hand_landmarker.task`)
- **OpenCV** - Video capture, HUD rendering, and frame processing
- **PyAutoGUI** - Desktop OS cursor control, clicking, and scrolling (lazy import, headless-safe)
- **google-genai** - Google Gemini LLM integration (`gemini-3.6-flash`, `gemini-2.5-flash`, `gemini-1.5-flash`)
- **python-dotenv** - Environment variable management
- **Flask** - Blueprint-based modular web server & REST API
- **Tailwind CSS** - Modern dark obsidian UI/UX design (zero AI slop)
- **PWA** - Web App Manifest (`manifest.json`), Service Worker (`sw.js`), native installation lifecycle

## Project Structure
```
Test2/
├── .env.example              # Environment variable template
├── .gitignore
├── requirements.txt          # Python dependencies
├── README.md                 # Full documentation
├── AGENTS.md                 # Architecture and agent guidelines
├── main.py                   # Application entry point & graceful shutdown
├── hand_landmarker.task      # MediaPipe hand model
├── config/
│   ├── __init__.py           # Config package exports
│   └── settings.py           # Type-safe configuration & command mappings
├── src/
│   ├── __init__.py           # Package exports
│   ├── core/
│   │   ├── __init__.py
│   │   └── logger.py         # Thread-safe activity ring buffer
│   ├── services/
│   │   ├── __init__.py
│   │   ├── system_service.py # SystemService class (volume & brightness)
│   │   ├── voice_service.py  # VoiceService class (speech recognition & parser)
│   │   ├── vision_service.py # VisionService class (MediaPipe landmarks & cursor)
│   │   ├── search_service.py # SearchService class (Gemini LLM integration)
│   │   ├── desktop_service.py # DesktopControlService (keyboard, media, apps, lock)
│   │   └── tts_service.py    # TTSService class (edge-tts neural text-to-speech)
│   ├── web/
│   │   ├── __init__.py
│   │   ├── app.py            # Flask app factory & startup
│   │   ├── routes.py         # Modular REST API routes & PWA endpoints
│   │   └── camera_stream.py  # Webcam capture & low-latency MJPEG streamer
│   ├── system_control.py     # Backward-compatible shim -> services.system_service
│   ├── voice_handler.py      # Backward-compatible shim -> services.voice_service
│   ├── hand_tracker.py       # Backward-compatible shim -> services.vision_service
│   ├── web_search.py         # Backward-compatible shim -> services.search_service
│   └── web_app.py            # Backward-compatible shim -> web.app
├── desktop/
│   ├── start_linux.sh        # Linux desktop app launcher (Chromium app-mode)
│   ├── start_windows.bat     # Windows desktop app launcher
│   ├── voicebot.desktop      # Linux .desktop launcher entry
│   └── VoiceBot.spec         # PyInstaller spec for native executable build
├── static/
│   ├── manifest.json         # PWA Web App Manifest
│   ├── sw.js                 # PWA Service Worker
│   ├── icons/                # High-res PWA & favicon assets
│   ├── css/
│   │   └── custom.css        # Fluid orb, range sliders, glassmorphism styles
│   └── js/
│       └── app.js            # PWA controller, Web Speech API, orb control, UI state
├── templates/
│   └── index.html            # Tailwind dashboard with interactive fluid orb
└── tests/
    ├── __init__.py
    ├── test_config.py        # Config tests
    ├── test_system_service.py# System control tests
    ├── test_voice_service.py # Voice parser tests
    ├── test_vision_service.py# Vision & gesture tests
    ├── test_search_service.py# Search service tests
    └── test_web_routes.py    # Flask REST API tests
```

## Setup & Execution
```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and set GEMINI_API_KEY

# Run test suite
.venv/bin/pytest -v

# Run the application
python main.py
# Opens browser at http://localhost:5000

# Run as a native desktop app (Linux)
./desktop/start_linux.sh
# Windows
desktop\start_windows.bat
```

## Architecture
- `main.py` - Initializes signal handlers, starts web server, opens browser, manages lifecycle.
- `config/settings.py` - Centralized, typed configuration with `.env` overrides and command dictionaries (including media/app/screenshot/lock voice commands).
- `src/core/logger.py` - Thread-safe activity and telemetry logger ring buffer.
- `src/services/system_service.py` - Cross-platform volume (`pactl`/`amixer`/`osascript`/`pycaw`) and brightness (`brightnessctl`/`light`/`xbacklight`/`sbc`) controller.
- `src/services/voice_service.py` - Command parsing with word boundary matching, number extraction, dual audio backend (`pyaudio` + `sounddevice`), and desktop control command routing.
- `src/services/vision_service.py` - MediaPipe v1.0 HandLandmarker with smoothed exponential moving average cursor movement, pinch-to-click, and middle finger scrolling.
- `src/services/search_service.py` - Google Gemini integration with automatic fallback models (`gemini-3.6-flash`, `gemini-2.5-flash`, `gemini-1.5-flash`).
- `src/services/desktop_service.py` - Full OS desktop control: screenshots, screen lock, media keys, app launching, clipboard, keyboard shortcuts (Linux + Windows).
- `src/services/tts_service.py` - Natural human-like text-to-speech via Microsoft edge-tts neural voices, with system TTS fallback.
- `src/web/camera_stream.py` - Background webcam capture loop with drop-frame queue preventing frame latency buildup.
- `src/web/routes.py` - REST API endpoints, PWA manifest (`/manifest.json`), service worker (`/sw.js`), MJPEG stream (`/video_feed`), and `/api/desktop/*` desktop control endpoints.
- `static/css/custom.css` - Fluid interactive orb (glow, pulse, ripples, waveform), range sliders, glassmorphism.
- `static/js/app.js` - Client-side PWA controller, Web Speech API speech recognition, natural voice selection, fluid orb state machine, Web Speech Synthesis (TTS), desktop control helpers, and gesture telemetry HUD.
- `templates/index.html` - Responsive Tailwind CSS dashboard with a tappable fluid AI assistant orb at the center.
