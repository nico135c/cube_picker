import cv2
import time as t
from cube_picker import CubePicker

def choose_cube(cubes, centers):
    print("Detected cubes:", list(zip(cubes, centers)))
    pick = input("Which color to pick? (color/none) ").strip().lower()
    if pick == "none" or pick not in cubes:
        return None
    idx = cubes.index(pick)
    return pick, centers[idx]

def main():
    picker = CubePicker(camera_index=0)
    try:
        print("Initializing…")
        picker.initialize(init_frames=12)
        print("Calibrating…")
        picker.calibrate(calib_frames=60)
        print("Ready.")

        detected_streak = 0
        while True:
            ok, frame = picker.cap.read()
            frame = cv2.rotate(frame, cv2.ROTATE_180)
            if not ok:
                continue

            frame = picker.crop_frame(frame)
            cubes, centers = picker.detect_cubes(frame)

            if cubes:
                detected_streak += 1
            else:
                detected_streak = 0

            if detected_streak > 60:
                choice = choose_cube(cubes, centers)
                if choice:
                    pick, (cx, cy) = choice
                    X, Y = picker.pixel_to_robot_xy(cx, cy)
                    print(f"Picking at robot XY: ({X:.1f}, {Y:.1f})")
                    picker.grasp(X, Y, pick)
                    t.sleep(2)
                detected_streak = 0

            cv2.imshow("Cropped", frame)
            if cv2.waitKey(1) == 27:  # ESC
                break

    finally:
        picker.close()

if __name__ == "__main__":
    main()
