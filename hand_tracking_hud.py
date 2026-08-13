"""
Hand Tracking HUD — real-time futuristic hand overlay + gesture-triggered effects.

Mendeteksi kedua tangan lewat webcam, menggambar overlay HUD (titik landmark,
garis penghubung, bounding box bersudut, jarak antar jari), dan memicu efek
visual saat gesture tertentu terdeteksi.

Gesture:
  - Pinch (ujung jempol menyentuh ujung telunjuk) -> efek yang sedang dipilih aktif,
    kembali normal begitu jari dilepas.
  - Peace sign (telunjuk + jari tengah terangkat, dua jari lain turun) -> blur otomatis.

Kontrol keyboard:
  1-6      pilih efek yang dipicu oleh gesture pinch
  s        simpan screenshot ke folder ini
  q / ESC  keluar

Install dulu:
  pip install opencv-python mediapipe numpy
"""

import time
import random

import cv2
import numpy as np
import mediapipe as mp

mp_hands = mp.solutions.hands

EFFECTS = ["blur", "crack", "invert", "glitch", "distort", "freeze"]
PINCH_THRESHOLD_PX = 35


class HandHUD:
    def __init__(self, cam_index=0, width=1280, height=720):
        self.hands = mp_hands.Hands(
            model_complexity=1,
            max_num_hands=2,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.6,
        )
        self.cam_index = cam_index
        self.width = width
        self.height = height
        self.active_effect_index = 0
        self.frozen_frame = None
        self.prev_time = time.time()

    # ---------- helpers ----------

    @staticmethod
    def distance(a, b):
        return float(np.hypot(a[0] - b[0], a[1] - b[1]))

    @staticmethod
    def is_peace(lm):
        def up(tip, pip):
            return lm[tip].y < lm[pip].y
        return up(8, 6) and up(12, 10) and not up(16, 14) and not up(20, 18)

    # ---------- HUD overlay ----------

    def draw_hud(self, frame, hand_landmarks, handedness_label, w, h):
        pts = [(int(p.x * w), int(p.y * h)) for p in hand_landmarks.landmark]
        color = (0, 255, 200) if handedness_label == "Right" else (255, 140, 0)

        for a, b in mp_hands.HAND_CONNECTIONS:
            cv2.line(frame, pts[a], pts[b], color, 1, cv2.LINE_AA)

        for i, p in enumerate(pts):
            r = 5 if i in (4, 8, 12, 16, 20) else 3
            cv2.circle(frame, p, r, color, -1, cv2.LINE_AA)
            cv2.circle(frame, p, r + 3, color, 1, cv2.LINE_AA)

        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        x0, x1, y0, y1 = min(xs) - 14, max(xs) + 14, min(ys) - 14, max(ys) + 14
        tick = 14
        for (cx, cy), dx, dy in [
            ((x0, y0), 1, 1), ((x1, y0), -1, 1),
            ((x0, y1), 1, -1), ((x1, y1), -1, -1),
        ]:
            cv2.line(frame, (cx, cy), (cx + tick * dx, cy), color, 2, cv2.LINE_AA)
            cv2.line(frame, (cx, cy), (cx, cy + tick * dy), color, 2, cv2.LINE_AA)

        dist = self.distance(pts[4], pts[8])
        cv2.putText(frame, f"{handedness_label.upper()}  d={dist:.0f}px",
                    (x0, max(y0 - 10, 14)), cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                    color, 1, cv2.LINE_AA)
        return pts, dist

    # ---------- effects ----------

    def apply_effect(self, frame, name):
        h, w = frame.shape[:2]

        if name == "blur":
            return cv2.GaussianBlur(frame, (35, 35), 0)

        if name == "invert":
            return cv2.bitwise_not(frame)

        if name == "glitch":
            out = frame.copy()
            for _ in range(6):
                y = random.randint(0, h - 12)
                bh = random.randint(4, 18)
                shift = random.randint(-40, 40)
                out[y:y + bh] = np.roll(out[y:y + bh], shift, axis=1)
            b, g, r = cv2.split(out)
            b = np.roll(b, 3, axis=1)
            r = np.roll(r, -3, axis=1)
            return cv2.merge([b, g, r])

        if name == "distort":
            out = frame.copy()
            t = time.time() * 4
            step = 6
            for y in range(0, h, step):
                shift = int(18 * np.sin(y / 24 + t))
                out[y:y + step] = np.roll(frame[y:y + step], shift, axis=1)
            return out

        if name == "crack":
            overlay = frame.copy()
            cx, cy = w // 2, h // 2
            for _ in range(9):
                ang = random.uniform(0, 2 * np.pi)
                pt = (cx, cy)
                for _ in range(5):
                    nx = pt[0] + random.randint(-40, 40) + int(np.cos(ang) * 20)
                    ny = pt[1] + random.randint(-40, 40) + int(np.sin(ang) * 20)
                    cv2.line(overlay, pt, (nx, ny), (235, 245, 255), 1, cv2.LINE_AA)
                    pt = (nx, ny)
            return cv2.addWeighted(overlay, 0.85, frame, 0.15, 0)

        if name == "freeze":
            if self.frozen_frame is None:
                self.frozen_frame = frame.copy()
            return self.frozen_frame

        return frame

    # ---------- main loop ----------

    def run(self):
        cap = cv2.VideoCapture(self.cam_index)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

        if not cap.isOpened():
            print("Tidak bisa membuka webcam.")
            return

        print("Hand Tracking HUD berjalan — tekan 'q' untuk keluar.")

        while True:
            ok, frame = cap.read()
            if not ok:
                break
            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = self.hands.process(rgb)

            pinch_active = False
            peace_active = False

            if result.multi_hand_landmarks and result.multi_handedness:
                for hand_landmarks, handedness in zip(
                    result.multi_hand_landmarks, result.multi_handedness
                ):
                    label = handedness.classification[0].label
                    _, dist = self.draw_hud(frame, hand_landmarks, label, w, h)
                    if dist < PINCH_THRESHOLD_PX:
                        pinch_active = True
                    if self.is_peace(hand_landmarks.landmark):
                        peace_active = True
            else:
                self.frozen_frame = None

            if peace_active:
                frame = self.apply_effect(frame, "blur")
            elif pinch_active:
                frame = self.apply_effect(frame, EFFECTS[self.active_effect_index])
            else:
                self.frozen_frame = None

            now = time.time()
            fps = 1 / (now - self.prev_time) if now > self.prev_time else 0
            self.prev_time = now
            status = f"FPS {fps:.0f}  EFEK[{self.active_effect_index + 1}] {EFFECTS[self.active_effect_index].upper()}"
            cv2.putText(frame, status, (16, h - 16), cv2.FONT_HERSHEY_SIMPLEX,
                        0.5, (0, 255, 200), 1, cv2.LINE_AA)

            cv2.imshow("Hand Tracking HUD", frame)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
            elif key == ord("s"):
                fname = f"snapshot_{int(time.time())}.png"
                cv2.imwrite(fname, frame)
                print(f"Tersimpan: {fname}")
            elif ord("1") <= key <= ord("6"):
                self.active_effect_index = key - ord("1")

        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    HandHUD().run()
