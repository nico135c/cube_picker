import cv2
import time as t
from cube_picker import CubePicker
from llm_grasp_selector import LLMGraspSelector

picker = CubePicker(camera_index=0)
selector = LLMGraspSelector()

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
            print("Detected cubes:", list(zip(cubes, centers)))
            user_command = input("Which cube to pick? (color/none) ").strip().lower()
            actions = selector.select_objects(cubes, centers, user_command)

            for color, center in actions:
                cx, cy = center
                X, Y = picker.pixel_to_robot_xy(cx, cy)
                picker.grasp(X, Y, color)
                t.sleep(2)
            detected_streak = 0

        cv2.imshow("Cropped", frame)
        if cv2.waitKey(1) == 27:  # ESC
            break

finally:
    picker.close()