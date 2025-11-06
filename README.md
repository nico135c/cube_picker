# MyCobot 280 PI – Color Cube Grasping

This project explores **vision-guided manipulation** with the [Elephant Robotics myCobot 280 Pi]([https://www.elephantrobotics.com/](https://www.elephantrobotics.com/en/mycobot-pi/)).  
It is developed as part of my work as a **student helper at the Department of Materials and Production (LAB)**.

## Current Features
- Uses the onboard camera to **detect colored cubes** on a workspace.  
- Prompts the user to **select a color** (via Python input).  
- Commands the myCobot to move and **grasp the chosen cube** with a fixed pick strategy.  

## Planned Features
- Integrate a **large language model (LLM)** interface so the user can simply **talk to the robot** in natural language instead of entering commands.   

## Purpose
This repository serves as a starting point for combining **computer vision**, **robotics**, and **AI-driven interaction** on a low-cost collaborative arm.  
It is intended both as a practical robotics project and as a demonstration of integrating LLMs into real-world lab tasks. 

## Code Attribution
Some parts of this code are adapted from the official Elephant Robotics examples:  
[elephantrobotics/mycobot_ros – aikit_280_pi/scripts](https://github.com/elephantrobotics/mycobot_ros/tree/noetic/mycobot_ai/aikit_280_pi/scripts)

# Robot Setup & Operation Guide

Follow these steps carefully to start up and operate the robot correctly.

---

## 1. Power On the Robot

- Press the **red ON/OFF switch** to power on the robot.  
- The robot should **start up automatically**, though it may take a little while — please be patient.

---

## 2. Connect to the Correct Wi-Fi

- Ensure the robot is connected to **eduroam**.  
- If it’s connected to **ElephantRobotics_AP**, **disconnect** and reconnect to **eduroam**.

---

## 3. *(Optional)* Enable TTS Voice Output

If you want the robot’s **Text-to-Speech (TTS)** voice to work:

1. Press the **settings icon** in the top-right corner.  
2. Go to: **System Settings → Sound → Output**  
3. Change the output device to **Jabra Speak 750 Analog Stereo**

---

## 4. Open the Project Folder

- Open a terminal window by pressing:
  ```bash
  CTRL + ALT + T
  ```  
- In the terminal, change into the project folder by running:
  ```bash
  cd cube_picker
  ```

**Explanation:**  
The command `cd cube_picker` means *“change directory to the folder named `cube_picker`”*. This tells the terminal to move into the robot’s project folder, where all the necessary files and scripts (like `main.py`) are stored.

---

## 5. Run the Main Program

- In the same terminal, start the program by running:
  ```bash
  python main.py
  ```

This will:
- Start all **calibration** and **initialization** processes.  
- Open a **camera feed** window once everything is ready.

---

## 6. Place Objects

- Place objects within the camera frame.

**!Important:**  
If you place objects **too close to the robot’s base**, it might **not be able to pick them up**.

---

## 7. Start Object Detection

- Focus the window titled **“Cropped”** (the camera feed window).  
- Press the `S` key to start detection.

The system will detect and list the objects visible in the frame.

---

## 8. Pick Up Objects

- Type which **objects** you want the robot to pick up.  
- The input is processed by the **LLM (Large Language Model)** and the robot will pick the selected cubes.

---

## 9. Repeat as Needed

- After the cubes are picked and the camera feed updates, you can place new objects and return to **Step 7**.

---
