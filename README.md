# MyCobot 280 PI – Color Cube Grasping

This project explores **vision-guided manipulation** with the [Elephant Robotics myCobot 280 Pi]([https://www.elephantrobotics.com/](https://www.elephantrobotics.com/en/mycobot-pi/)).  
It is developed as part of my work as a **student helper at the Department of Materials and Production (LAB)**.

## Current Features
- Uses the onboard camera to **detect colored cubes** on a workspace.  
- Prompts the user to **select a color** (via Python input).  
- Commands the myCobot to move and **grasp the chosen cube** with a fixed pick strategy.  

## Planned Features
- Integrate a **large language model (LLM)** interface so the user can simply **talk to the robot** in natural language instead of entering commands.  
- Extend to more flexible perception (e.g., shapes, object IDs) and smarter grasp planning.  

## Purpose
This repository serves as a starting point for combining **computer vision**, **robotics**, and **AI-driven interaction** on a low-cost collaborative arm.  
It is intended both as a practical robotics project and as a demonstration of integrating LLMs into real-world lab tasks. 

## Code Attribution
Some parts of this code are adapted from the official Elephant Robotics examples:  
[elephantrobotics/mycobot_ros – aikit_280_pi/scripts](https://github.com/elephantrobotics/mycobot_ros/tree/noetic/mycobot_ai/aikit_280_pi/scripts)
