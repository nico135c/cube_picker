#!/usr/bin/env python3
import cv2
import numpy as np
import json
import argparse
import os
from datetime import datetime

WINDOW_MAIN = "HSV Range Finder"
WINDOW_MASK = "Mask"
WINDOW_RESULT = "Result"

# Defaults (broad; good starting point)
DEFAULTS = {
    "H_MIN": 0,
    "S_MIN": 0,
    "V_MIN": 0,
    "H_MAX": 179,
    "S_MAX": 255,
    "V_MAX": 255,
}

def nothing(_):
    pass

def add_trackbars():
    cv2.namedWindow(WINDOW_MAIN, cv2.WINDOW_NORMAL)
    cv2.createTrackbar("H_MIN", WINDOW_MAIN, DEFAULTS["H_MIN"], 179, nothing)
    cv2.createTrackbar("S_MIN", WINDOW_MAIN, DEFAULTS["S_MIN"], 255, nothing)
    cv2.createTrackbar("V_MIN", WINDOW_MAIN, DEFAULTS["V_MIN"], 255, nothing)

    cv2.createTrackbar("H_MAX", WINDOW_MAIN, DEFAULTS["H_MAX"], 179, nothing)
    cv2.createTrackbar("S_MAX", WINDOW_MAIN, DEFAULTS["S_MAX"], 255, nothing)
    cv2.createTrackbar("V_MAX", WINDOW_MAIN, DEFAULTS["V_MAX"], 255, nothing)

    # Optional simple morphology controls
    cv2.createTrackbar("Blur ksize (odd)", WINDOW_MAIN, 1, 31, nothing)   # 1 means no blur
    cv2.createTrackbar("Open iters", WINDOW_MAIN, 0, 5, nothing)
    cv2.createTrackbar("Close iters", WINDOW_MAIN, 0, 5, nothing)

def get_ranges_from_trackbar():
    h_min = cv2.getTrackbarPos("H_MIN", WINDOW_MAIN)
    s_min = cv2.getTrackbarPos("S_MIN", WINDOW_MAIN)
    v_min = cv2.getTrackbarPos("V_MIN", WINDOW_MAIN)

    h_max = cv2.getTrackbarPos("H_MAX", WINDOW_MAIN)
    s_max = cv2.getTrackbarPos("S_MAX", WINDOW_MAIN)
    v_max = cv2.getTrackbarPos("V_MAX", WINDOW_MAIN)

    # clamp to valid order (ensure min <= max)
    h_min, h_max = min(h_min, h_max), max(h_min, h_max)
    s_min, s_max = min(s_min, s_max), max(s_min, s_max)
    v_min, v_max = min(v_min, v_max), max(v_min, v_max)

    lower = np.array([h_min, s_min, v_min], dtype=np.uint8)
    upper = np.array([h_max, s_max, v_max], dtype=np.uint8)

    blur_ksize = cv2.getTrackbarPos("Blur ksize (odd)", WINDOW_MAIN)
    open_iters = cv2.getTrackbarPos("Open iters", WINDOW_MAIN)
    close_iters = cv2.getTrackbarPos("Close iters", WINDOW_MAIN)

    # make blur_ksize odd (0 or 1 => no blur)
    if blur_ksize % 2 == 0:
        blur_ksize = max(1, blur_ksize - 1)

    return lower, upper, blur_ksize, open_iters, close_iters

def apply_pipeline(frame_bgr, lower, upper, blur_ksize, open_iters, close_iters):
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)

    if blur_ksize > 1:
        hsv = cv2.GaussianBlur(hsv, (blur_ksize, blur_ksize), 0)

    mask = cv2.inRange(hsv, lower, upper)

    if open_iters > 0:
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, None, iterations=open_iters)
    if close_iters > 0:
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, None, iterations=close_iters)

    result = cv2.bitwise_and(frame_bgr, frame_bgr, mask=mask)
    return mask, result

def print_ranges(lower, upper):
    text = (
        f"OpenCV HSV ranges:\n"
        f"Lower: [{int(lower[0])}, {int(lower[1])}, {int(lower[2])}]\n"
        f"Upper: [{int(upper[0])}, {int(upper[1])}, {int(upper[2])}]\n"
        f"(Hue 0–179, Sat 0–255, Val 0–255)"
    )
    print(text)

def write_ranges(lower, upper, out_path="hsv_ranges.json"):
    payload = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "lower": [int(x) for x in lower],
        "upper": [int(x) for x in upper],
        "note": "OpenCV HSV (Hue 0–179, Sat/Val 0–255)"
    }
    # Avoid overwriting by default; append an index if exists
    base, ext = os.path.splitext(out_path)
    candidate = out_path
    idx = 1
    while os.path.exists(candidate):
        candidate = f"{base}_{idx}{ext}"
        idx += 1
    with open(candidate, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"Saved HSV ranges to: {candidate}")

def reset_sliders():
    for name, val in DEFAULTS.items():
        cv2.setTrackbarPos(name, WINDOW_MAIN, val)
    cv2.setTrackbarPos("Blur ksize (odd)", WINDOW_MAIN, 1)
    cv2.setTrackbarPos("Open iters", WINDOW_MAIN, 0)
    cv2.setTrackbarPos("Close iters", WINDOW_MAIN, 0)

def main():
    parser = argparse.ArgumentParser(description="Interactive HSV range tuner for OpenCV.")
    src = parser.add_mutually_exclusive_group()
    src.add_argument("--image", type=str, help="Path to an image file.")
    src.add_argument("--video", type=str, help="Path to a video file.")
    parser.add_argument("--camera", type=int, default=0, help="Webcam index (default: 0).")
    parser.add_argument("--scale", type=float, default=1.0, help="Resize display (e.g., 0.75 or 0.5).")
    args = parser.parse_args()

    add_trackbars()
    cv2.namedWindow(WINDOW_MASK, cv2.WINDOW_NORMAL)
    cv2.namedWindow(WINDOW_RESULT, cv2.WINDOW_NORMAL)

    cap = None
    single_frame = None
    video_mode = False

    if args.image:
        img = cv2.imread(args.image)
        if img is None:
            print(f"Failed to load image: {args.image}")
            return
        single_frame = img
    elif args.video:
        cap = cv2.VideoCapture(args.video)
        if not cap.isOpened():
            print(f"Failed to open video: {args.video}")
            return
        video_mode = True
    else:
        cap = cv2.VideoCapture(args.camera)
        if not cap.isOpened():
            print(f"Failed to open camera index {args.camera}")
            return

    reset_sliders()

    while True:
        if single_frame is not None:
            frame = single_frame.copy()
        else:
            ret, frame = cap.read()
            if not ret:
                if video_mode:
                    # loop video
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                else:
                    print("Failed to read frame from source.")
                    break

        if args.scale != 1.0:
            frame = cv2.resize(frame, None, fx=args.scale, fy=args.scale)

        lower, upper, blur_ksize, open_iters, close_iters = get_ranges_from_trackbar()
        mask, result = apply_pipeline(frame, lower, upper, blur_ksize, open_iters, close_iters)

        # put text overlay with quick info
        info = f"L:{lower.tolist()}  U:{upper.tolist()}  Blur:{blur_ksize}  Open:{open_iters}  Close:{close_iters}"
        disp = frame.copy()
        cv2.putText(disp, info, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,0), 3, cv2.LINE_AA)
        cv2.putText(disp, info, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 1, cv2.LINE_AA)

        cv2.imshow(WINDOW_MAIN, disp)
        cv2.imshow(WINDOW_MASK, mask)
        cv2.imshow(WINDOW_RESULT, result)

        key = cv2.waitKey(1) & 0xFF
        if key in (27, ord('q')):  # Esc or q
            break
        elif key == ord('p'):
            print_ranges(lower, upper)
        elif key == ord('w'):
            write_ranges(lower, upper, "hsv_ranges.json")
        elif key == ord('r'):
            reset_sliders()

    if cap is not None:
        cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()