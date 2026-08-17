# AGENTS.md

Static single-page site ("PERKAKAS", https://perkakas.id) + one standalone Python script. No build, test, or lint tooling — `index.html` is the entire app.

## The two files

- `index.html` — whole app (CSS + all JS inline, one IIFE per tool, no modules). All UI copy is in Indonesian; keep new copy in Indonesian.
- `hand_tracking_hud.py` — standalone OpenCV/MediaPipe webcam script. The Webcam panel downloads it via a relative link (`index.html`, `pyDownload` handler), so **never rename or move it** — that breaks the download button.

## index.html structure

- Nav tiles are generated from the `TOOLS` array; panels are matched by `data-panel` key. Add a tool by adding a panel div + entry in `TOOLS`. Six tools: kompres, resize, konversi, palet, qr, webcam.
- `filePreviewEl(file)` (shared helper) renders image/video/audio/file chip previews; the kompres/konversi/resize panels all show one after a file is picked.
- Webcam tool: in-browser real-time hand tracking via MediaPipe Tasks Vision WASM (`@mediapipe/tasks-vision@0.10.14` vision_bundle.js + wasm dir, `HandLandmarker` with hand_landmarker.task from storage.googleapis.com, GPU delegate with CPU fallback). Detections run in the existing rAF loop (`draw()`): gestures `PINCH` (thumb+index touch, 180ms latch) trigger the selected effect, `PEACE` (index+middle up, ring+pinky down) auto-blurs while held; HUD skeleton + badge (`camBadge`) show hands count/gesture. JS effects (blur, invert, glitch, distort, crack, freeze) mirror the Python script's `EFFECTS` list and gestures — keep both in sync if you change effects.
- External CDN deps (all lazy except the first two):
  - eager: Google Fonts, `qrcode-generator` 1.4.4 (cdnjs, replaces old qrcodejs — the QR panel renders canvas/SVG itself from `qr.isDark()`).
  - lazy: `@ffmpeg/ffmpeg@0.12.10` esm + `@ffmpeg/core@0.12.6` esm (single-thread build, works on GitHub Pages WITHOUT COOP/COEP headers), `pdf-lib@1.17.1`, `gif.js` 0.2.0 (cdnjs, worker loaded via text-fetch + blob), `@mediapipe/tasks-vision@0.10.14` (webcam hand tracking).
- FFmpeg integration gotchas (rarely obvious, hard-won):
  - Old API (`@ffmpeg/ffmpeg@0.11.x` + createFFmpeg, and `@ffmpeg/core@0.11.x`) is BROKEN on static hosts — the pthread core requires SharedArrayBuffer (needs COOP/COEP headers GitHub Pages can't set).
  - Working combo: dynamic `import()` of 0.12.10 ESM + blob module-worker (worker.js text-fetched, its `"./const.js"`/`"./errors.js"` imports rewritten to absolute CDN URLs) + `classWorkerURL` load option + esm core. See `ensureFfmpeg()`.
  - `file://` MUST be blocked before loading ffmpeg (raise `FILE_ONLY`) — worker spawn under null origin crashes the renderer tab.
  - New API has no `FS('stat')` — target-size search checks sizes via `readFile(...).length`.
- Verify changes by opening the file in a browser. `file://` covers everything except media conversion (needs http(s)/localhost).

## hand_tracking_hud.py

- Run: `pip install opencv-python mediapipe numpy` then `python hand_tracking_hud.py` (add `--cam 1` for another webcam). Needs a webcam.
- Controls: `1-6` select pinch-triggered effect (numpad works too), `s` saves screenshot, `q`/`ESC` quits. HUD shows FPS, pinch distance, and PINCH/PEACE tags.
- Gesture latch anti-blinking: `N_START_FRAMES` (pinch must persist 2 frames) / `N_RELEASE_FRAMES` (6 frames miss to release) — mirrors the browser version's 180ms latch; keep in sync.

## Vercel (opsional, siap pakai)

- `vercel.json` menyetel `Cross-Origin-Opener-Policy: same-origin` + `Cross-Origin-Embedder-Policy: credentialless` → SharedArrayBuffer tersedia (ffmpeg core multithread bisa dipakai). Semua CDN yang dipakai sudah mengirim `CORP: cross-origin`, jadi aman.
- Site tetap bekerja tanpa Vercel — ffmpeg memakai core single-thread yang jalan di GitHub Pages tanpa header. Jangan ubah mekanisme `ensureFfmpeg()` agar tetap universal.

## Git

- Origin adalah `github.com/hanifaufapc/toolsssssss`; deploy = commit + push ke `main` (GitHub Pages melayani itu). Pesan commit di repo seperti `Update index.html`.