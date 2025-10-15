"""
LLM-based Object Grasp Selector

This script uses an LLM (via OpenRouter API) to interpret user commands
and select which detected object(s) to grasp based on object detection results.

Features:
- Single object selection: "pick the red cube"
- Sequence of actions: "pick the red cube first, then pick the blue one"
- Natural language responses: LLM explains what it sees and plans to do
- Streaming responses: See the LLM's thought process in real-time

Usage Example:
    from llm_grasp_selector import LLMGraspSelector, grasp_object
    
    # Your object detection results
    objects = ["red", "blue", "green"]
    centers = [(100, 150), (200, 180), (150, 220)]
    
    # Initialize selector
    selector = LLMGraspSelector()
    
    # Get user command and select object(s)
    user_command = "pick the blue cube then the red one"
    actions = selector.select_objects(objects, centers, user_command)
    
    # Execute actions in sequence
    for color, center in actions:
        grasp_object(center, color)
"""

import os
import json
from openai import OpenAI

class LLMGraspSelector:
    """Handler for LLM-based object selection for grasping."""
    
    def __init__(self, api_key=None):
        """
        Initialize the LLM client.
        
        Args:
            api_key: OpenRouter API key. If None, reads from OPENROUTER_API_KEY env variable.
        """
        if api_key is None:
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                raise ValueError("API key must be provided or set in OPENROUTER_API_KEY environment variable")
        
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        self.model = "z-ai/glm-4.5-air:free"
    
    def select_objects(self, objects, centers, user_command):
        """
        Use LLM to select which object(s) to grasp based on user command.
        Supports sequences of actions.
        
        Args:
            objects: List of strings representing object colors (e.g., ['red', 'blue', 'green'])
            centers: List of coordinate tuples/lists, index-aligned with objects
            user_command: String command from user (e.g., "pick the red cube then the blue one")
        
        Returns:
            list: List of tuples [(color1, center1), (color2, center2), ...] in execution order
                  Returns empty list if no valid selection
        """
        if len(objects) != len(centers):
            raise ValueError("objects and centers lists must have the same length")
        
        if not objects:
            print("No objects detected!")
            return []
        
        # Create a structured representation of available objects
        available_objects = []
        for idx, (color, center) in enumerate(zip(objects, centers)):
            available_objects.append({
                "index": idx,
                "color": color,
                "center": center
            })
        
        # Construct the system prompt
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

Do not include any additional text outside the JSON object."""
        
        # Construct the user message
        user_message = f"""Available objects:
{json.dumps(available_objects, indent=2)}

User command: "{user_command}"

Which object(s) should be grasped and in what order?"""
        
        # Call the LLM with streaming
        try:
            stream = self.client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": "https://mycobot-project.local",
                    "X-Title": "MyCobot LLM Grasp Selector",
                },
                extra_body={},
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3,  # Lower temperature for more deterministic responses
                stream=True,  # Enable streaming
            )
            
            # Accumulate the streamed response
            #print("\n[LLM Response]")
            response_text = ""
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    #print(content, end="", flush=True)
                    response_text += content
            #print("\n")  # Add newline after streaming completes
            
            response_text = response_text.strip()
            
            # Parse the JSON response
            # Handle potential markdown code blocks
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            response_data = json.loads(response_text)
            
            # Extract the user response, actions, and reasoning
            user_response = response_data.get("response", "")
            actions = response_data.get("actions", [])
            reasoning = response_data.get("reasoning", "No reasoning provided")
            
            # Display the friendly response to the user
            #if user_response:
                #print(f"\n[ASSISTANT] {user_response}\n")
            
            #print(f"[TECHNICAL] {reasoning}")
            
            if not actions:
                print("[INFO] No valid objects selected")
                return []
            
            # Validate and extract all actions
            selected_actions = []
            for action_idx, action in enumerate(actions):
                index = action.get("index")
                color = action.get("color")
                center = action.get("center")
                
                if index is not None and color and center:
                    # Validate the index
                    if 0 <= index < len(objects):
                        selected_actions.append((color, center))
                        #print(f"[ACTION {action_idx + 1}] {color} at {center}")
                    else:
                        print(f"[ERROR] Invalid index {index} in action {action_idx + 1}")
                else:
                    print(f"[ERROR] Incomplete action data in action {action_idx + 1}")
            
            return user_response, selected_actions
                
        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse LLM response as JSON: {e}")
            print(f"Response was: {response_text}")
            return []
        except Exception as e:
            print(f"[ERROR] LLM call failed: {e}")
            return []
