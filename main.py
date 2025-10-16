import cv2
import time as t
from cube_picker import CubePicker
from llm_grasp_selector import LLMGraspSelector
from vosk_stt import VoskSTT
from tts import TTS

def main():
    picker = CubePicker(camera_index=0)
    stt = VoskSTT()
    tts = TTS()
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
                print("=== LLM-Based Grasp Selector ===\n")
                tts.speak(f"I have detected {len(cubes)} cubes")
                for idx, (cube, center) in enumerate(zip(cubes, centers)):
                    tts.speak(f"A {cube} cube at point {center}")
                tts.speak("Which cube or cubes do you want to pick?")
                user_command = stt.speech_to_text_vosk()
                #user_command = input("\nEnter your command (or 'quit' to exit): ").strip()
            
                if user_command.lower() in ['quit', 'exit', 'q']:
                    print("Exiting...")
                    break
                
                if not user_command:
                    continue

                user_response, actions = selector.select_objects(cubes, centers, user_command)

                tts.speak(user_response)

                print(f"\n[EXECUTING] {len(actions)} action(s)")
                for idx, (color, center) in enumerate(actions):
                    print(f"\n--- Step {idx}/{len(actions)} ---")
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

if __name__ == "__main__":
    main()
