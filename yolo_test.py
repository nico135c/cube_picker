import cv2
import time as t
from cube_picker_yolo_test import CubePicker
from llm_grasp_selector import LLMGraspSelector
from vosk_stt import VoskSTT
from tts import BlockingTTS

def main():
    picker = CubePicker(camera_index=0)
    #stt = VoskSTT()
    #tts = BlockingTTS()
    try:
        selector = LLMGraspSelector()
    except ValueError as e:
        print(f"[ERROR] {e}")
        print("\nPlease set your OpenRouter API key:")
        print("  export OPENROUTER_API_KEY='your-api-key-here'")
        return

    try:
        print("Initializing…")
        picker.initialize(init_frames=12)
        print("Calibrating…")
        picker.calibrate(calib_frames=60)
        print("Ready.")

        detect = False
        while True:
            ok, frame = picker.cap.read()
            frame = cv2.rotate(frame, cv2.ROTATE_180)
            if not ok:
                continue

            frame = picker.crop_frame(frame)

            if detect:
                objects, centers = picker.detect_objects(frame)
                print("=== LLM-Based Grasp Selector ===\n")
                print(f"I have detected {len(objects)} objects")
                #tts.speak(f"I have detected {len(objects)} objects")
                for idx, (obj, center) in enumerate(zip(objects, centers)):
                    print(f"A {obj} at point {center}")
                    #tts.speak(f"A {obj} at point {center}")
                
                #tts.speak("Which object or objects do you want to pick?")
                #user_command = stt.speech_to_text_vosk()
                user_command = input("Which object or objects do you want to pick?")
            
                if user_command.lower() in ['quit', 'exit', 'q']:
                    print("Exiting...")
                    break
                
                if not user_command:
                    continue

                user_response, actions = selector.select_objects(objects, centers, user_command)

                #tts.speak(user_response)
                print(user_response)

                print(f"\n[EXECUTING] {len(actions)} action(s)")
                for idx, (obj, center) in enumerate(actions):
                    print(f"\n--- Step {idx + 1}/{len(actions)} ---")
                    picked = False
                    while not picked:
                        cx, cy = center
                        X, Y = picker.pixel_to_robot_xy(cx, cy)
                        picker.grasp(X, Y, obj)
                        # CHECK IF OBJECT WAS ACTUALLY PICKED
                        _, new_frame = picker.cap.read()
                        new_frame = cv2.rotate(new_frame, cv2.ROTATE_180)
                        new_objects, new_centers = picker.detect_objects(new_frame)
                        print(f"\n[INFO] Remaining objects after picking: {new_objects}")
                        if obj not in new_objects:
                            print(f"\n[INFO] Succesfully picked object: {obj}")
                            picked = True
                        else:
                            center = new_centers[new_objects.index(obj)]
                            print(f"\n[INFO] Failed to pick object: {obj}. Trying again with new center: {center}.")
                            picked = True
                        t.sleep(2)
                
                detect = False
            
            cv2.imshow("Cropped", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC
                break
            
            if key == ord('s'):
                detect = True
                

    finally:
        picker.close()

if __name__ == "__main__":
    main()
