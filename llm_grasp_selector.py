import os
import json
from omegaconf import DictConfig
from llm_agent import LLM_Agent


class LLMGraspSelector:
    """Handler for LLM-based object selection for grasping using a custom LLM_Agent."""

    def __init__(self):
        """
        Initialize the custom LLM agent instead of OpenAI/OpenRouter.
        system_prompt remains identical to your original prompt.
        """

        system_prompt = """You are a robotic assistant that helps select objects for grasping.
You will be given a list of detected objects with their colors and positions, and a user command.
Your task is to determine which object(s) the user wants to grasp based on their command.

The user may request a single object OR a sequence of objects to be grasped in order.

Respond ONLY with a JSON object in the following format:
{
    "response": "<A friendly, natural response to the user explaining what you see and what you plan to do. For example: 'I can see the leftmost object is red at position (100, 150), and the rightmost object is blue at position (300, 200). I will grasp them one by one.'>",
    "actions": [
        {
            "index": <index of the object>,
            "color": "<color of the object>",
            "center": <coordinates of the object>
        },
        {
            "index": <index of the next object>,
            "color": "<color of the next object>",
            "center": <coordinates of the next object>
        }
    ],
    "reasoning": "<brief technical explanation of your interpretation and action sequence>"
}

For a single object, the "actions" array will have one element.
For multiple objects (e.g., "pick red then blue"), the "actions" array will have multiple elements in the requested order.

If the user's command is unclear or no matching object is found, respond with:
{
    "response": "<A friendly explanation to the user about why you cannot fulfill their request>",
    "actions": [],
    "reasoning": "<technical explanation of why no object was selected>"
}

The "response" field should always be friendly and conversational, explaining to the user what you understand and what you will do.

Do not include any additional text outside the JSON object.
"""

        # Build Hydra/OmegaConf config object to pass to LLM_Agent
        llm_cfg = DictConfig({
            "model_name": "phi4:latest",
            "url": "http://172.27.15.38:11434/api/generate",
            "max_retries": 3,
            "system_prompt": system_prompt
        })

        # Initialize your custom LLM
        self.llm = LLM_Agent(llm_cfg)


    def select_objects(self, objects, centers, user_command):
        """Use your custom LLM_Agent to select objects."""

        if len(objects) != len(centers):
            raise ValueError("objects and centers lists must have the same length")

        if not objects:
            print("No objects detected!")
            return []

        available_objects = [
            {"index": i, "color": color, "center": center}
            for i, (color, center) in enumerate(zip(objects, centers))
        ]

        # Construct user prompt appended after system prompt
        user_prompt = f"""
Available objects:
{json.dumps(available_objects, indent=2)}

User command: "{user_command}"

Which object(s) should be grasped and in what order?
"""

        # --- Call your custom LLM ---
        try:
            result = self.llm.process_request(user_prompt)
            # result is a list (your agent wraps dicts into a list)
            response = result[0]

        except Exception as e:
            print(f"[ERROR] LLM failed: {e}")
            return []


        # --- Extract fields ---
        user_response = response.get("response", "")
        actions = response.get("actions", [])
        reasoning = response.get("reasoning", "")

        # Print for user (optional)
        print("\n[ASSISTANT]", user_response)
        print("[TECHNICAL]", reasoning)

        # No actions selected
        if not actions:
            print("[INFO] No valid objects selected")
            return []

        selected_actions = []

        for a in actions:
            idx = a.get("index")
            color = a.get("color")
            center = a.get("center")

            if idx is None or color is None or center is None:
                print("[ERROR] Incomplete action:", a)
                continue

            if 0 <= idx < len(objects):
                selected_actions.append((color, center))
            else:
                print("[ERROR] Invalid index:", idx)

        return user_response, selected_actions