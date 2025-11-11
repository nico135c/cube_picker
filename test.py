import cv2
import time as t
from cube_picker import CubePicker
from llm_grasp_selector import LLMGraspSelector
from vosk_stt import VoskSTT
from tts import BlockingTTS

def main():
    picker = CubePicker(camera_index=0)
    try:
        print("Initializing…")
        picker.initialize(init_frames=12)
        print("Calibrating…")
        picker.calibrate(calib_frames=60)
        print("Ready.")

        detect = False
        annotated_frame = None
        while True:
            ok, frame = picker.cap.read()
            frame = cv2.rotate(frame, cv2.ROTATE_180)
            if not ok:
                continue

            frame = picker.crop_frame(frame)

            if detect:
                objects, centers, annotated_frame = picker.detect_objects(frame)
                print("=== LLM-Based Grasp Selector ===\n")
                print(f"I have detected {len(objects)} objects")
                for idx, (obj, center) in enumerate(zip(objects, centers)):
                    print(f"A {obj} at point {center}")
                
                detect = False
            
            if annotated_frame is not None:
                cv2.imshow("Detections", annotated_frame)
            cv2.imshow("Cropped", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC
                break
            
            if key == ord('s'):
                detect = True
                

    finally:
        picker.close()
        cv2.destroyAllWindows()

main()
