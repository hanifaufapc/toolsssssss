# AGENTS.md

Static single-page site ("PERKAKAS", https://perkakas.id). No build, test, or lint tooling — `index.html` is the entire app and the only file.

## index.html structure

- Nav tiles are generated from the `TOOLS` array; panels are matched by `data-panel` key. Add a tool by adding a panel div + entry in `TOOLS`. Six tools: kompres, resize, konversi, palet, qr, webcam.
- `filePreviewEl(file)` (shared helper) renders image/video/audio/file chip previews; the kompres/konversi/resize panels all show one after a file is picked.
- Webcam tool: in-browser real-time hand tracking via MediaPipe Tasks Vision WASM. **Self-hosted** di `vendor/tasks-vision/` (vision_bundle.mjs + wasm/ + hand_landmarker.task, ~18 MB) karena `@mediapipe/tasks-vision@0.10.14` TIDAK punya `vision_bundle.js` (hanya `.mjs`/`.cjs`) dan CDN jsdelivr/unpkg kerap diblokir ISP Indonesia. `loadHands()` memakai dynamic `import()` ESM: sumber lokal dulu, lalu CDN mirror; model GPU → CPU → CDN fallback. Detections run throttled (~25fps) in the existing rAF loop (`draw()`): gestures `PINCH` (thumb+index touch, 180ms latch) trigger the selected effect, `PEACE` (index+middle up, ring+pinky down) auto-blurs while held; HUD skeleton + badge (`camBadge`) show hands count/gesture. Effects (blur, invert, glitch, distort, crack, freeze) live only in the browser version — the Python script was removed. Jangan set `baseOptions.modelAssetPath` via URL berbeda tanpa fallback ke `vendor/`.
- External CDN deps (all lazy except the first two):
  - eager: Google Fonts, `qrcode-generator` 1.4.4 (cdnjs, replaces old qrcodejs — the QR panel renders canvas/SVG itself from `qr.isDark()`).
  - lazy: `@ffmpeg/ffmpeg@0.12.10` esm + `@ffmpeg/core@0.12.6` esm (single-thread build, works on GitHub Pages WITHOUT COOP/COEP headers), `pdf-lib@1.17.1`, `gif.js` 0.2.0 (cdnjs, worker loaded via text-fetch + blob). MediaPipe tasks-vision TIDAK lewat CDN — self-hosted (lihat bagian webcam).
- FFmpeg integration gotchas (rarely obvious, hard-won):
  - Old API (`@ffmpeg/ffmpeg@0.11.x` + createFFmpeg, and `@ffmpeg/core@0.11.x`) is BROKEN on static hosts — the pthread core requires SharedArrayBuffer (needs COOP/COEP headers GitHub Pages can't set).
  - Working combo: dynamic `import()` of 0.12.10 ESM + blob module-worker (worker.js text-fetched, its `"./const.js"`/`"./errors.js"` imports rewritten to absolute CDN URLs) + `classWorkerURL` load option + esm core. See `ensureFfmpeg()`.
  - `file://` MUST be blocked before loading ffmpeg (raise `FILE_ONLY`) — worker spawn under null origin crashes the renderer tab.
  - New API has no `FS('stat')` — target-size search checks sizes via `readFile(...).length`.
- Verify changes by opening the file in a browser. `file://` covers everything except media conversion (needs http(s)/localhost).

## Vercel (opsional, siap pakai)

- `vercel.json` menyetel `Cross-Origin-Opener-Policy: same-origin` + `Cross-Origin-Embedder-Policy: credentialless` → SharedArrayBuffer tersedia (ffmpeg core multithread bisa dipakai). Semua CDN yang dipakai sudah mengirim `CORP: cross-origin`, jadi aman.
- Site tetap bekerja tanpa Vercel — ffmpeg memakai core single-thread yang jalan di GitHub Pages tanpa header. Jangan ubah mekanisme `ensureFfmpeg()` agar tetap universal.

## Git

- Origin adalah `github.com/hanifaufapc/toolsssssss`; deploy = commit + push ke `main` (GitHub Pages melayani itu). Pesan commit di repo seperti `Update index.html`.