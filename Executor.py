import base64
import os
import re
import subprocess
import sys
import time
from google import genai
from google.genai import types
from groq import Groq
import traceback

class AICommandExecutor:
    def __init__(self, api_key="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", model="qwen-2.5-coder-32b", max_retries=5):
        self.api_key = api_key
        self.model = model
        self.max_retries = max_retries
        self.executed_scripts = {}
        self.script_counter = 1
        # self.client = genai.Client(api_key=self.api_key)
        self.client = Groq(api_key="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")
    def extract_code_blocks(self, response_text):
        """Extract bash and python code blocks from the response text."""
        # Extract bash commands
        bash_pattern = r"bash`(.*?)`"
        bash_match = re.search(bash_pattern, response_text, re.DOTALL)
        bash_commands = bash_match.group(1) if bash_match else "None"
        
        # Extract python code
        python_pattern = r"python```(.*?)```"
        python_match = re.search(python_pattern, response_text, re.DOTALL)
        python_code = python_match.group(1) if python_match else None
        
        return bash_commands, python_code
    
    def execute_bash(self, bash_commands):
        """Execute bash commands if they are not 'None'."""
        if bash_commands.strip().lower() == "none":
            print("No packages to install.")
            return True, "No packages to install."
        
        print("\n[Installing packages...]")
        try:
            result = subprocess.run(bash_commands, shell=True, check=True, 
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True)
            print(result.stdout)
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            error_msg = f"Bash execution error: {e}\n{e.stderr}"
            print(error_msg)
            return False, error_msg
    
    def execute_python(self, python_code, script_name):
        """Execute python code by saving it to a file and running it."""
        if not python_code:
            return True, "No Python code to execute."
        
        # Save the python code to a file
        with open(script_name, "w") as file:
            file.write(python_code)
        
        print(f"\n[Executing Python script: {script_name}]")
        try:
            result = subprocess.run([sys.executable, script_name], 
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True)
            if result.returncode != 0:
                error_msg = f"Python execution error:\n{result.stderr}"
                print(error_msg)
                return False, error_msg
            
            print(result.stdout)
            return True, result.stdout
        except Exception as e:
            error_msg = f"Exception during Python execution: {str(e)}\n{traceback.format_exc()}"
            print(error_msg)
            return False, error_msg
    
    def generate_ai_response(self, user_query, error_context=None):
        """Generate response from AI model."""

        contents = [
                {
                    "role": "system",
                    "content": "Your GrandAssist, You are an AI powered system control program for Grandpa's, thing is they mostly don't know how to control computers, but you my friend will help them with that. You will write python code which can be used for controlling the system, for example,\nGrandpa : Hey I want u to increase my screen brightness\nGrandAssist : Ok here you go,\nbash`pip install screen-brightness-control`\npython```\nimport screen_brightness_control as sbc\n# Increase brightness by 30% (adjust as needed)\ncurrent_brightness = sbc.get_brightness(display=0)\nnew_brightness = min(current_brightness[0] + 30, 100)\n# Set new brightness\nsbc.set_brightness(new_brightness, display=0)\nprint(f\\\"Brightness set to {new_brightness}%\\\")\n```\nIs it clear now?\nGrandpa: Hey show a prompt window pop up and say u are hacked\nGrandAssist: Okay here you go,\nbash`None`\npython```\nimport tkinter as tk\nfrom tkinter import messagebox\ndef show_popup():\n root = tk.Tk()\n root.withdraw() # Hide root window\n messagebox.showerror(\\\"Security Alert\\\", \\\"You Are Hacked!\\\") # Popup with error style\nshow_popup()\n```\nGrandpa: Take a screenshot\nGrandAssist: Ok taking a screenshot\nbash`pip install pyautogui`\npython```\nimport pyautogui\n# Take screenshot\nscreenshot = pyautogui.screenshot()\n# Save screenshot\nscreenshot.save(\\\"screenshot.png\\\")\nprint(\\\"Screenshot saved as 'screenshot.png'\\\")\n```\nHope it helped.\nGrandpa: take a photo using the webcam\nGrandAssist: Taking a photo\nbash`pip install opencv-python`\npython```\nimport cv2\n# Open camera (0 is usually the default camera)\ncamera = cv2.VideoCapture(0)\nif not camera.isOpened():\n print(\\\"Error: Could not access the camera.\\\")\n exit()\n# Capture frame\nret, frame = camera.read()\nif ret:\n # Save photo\n cv2.imwrite(\\\"photo.png\\\", frame)\n print(\\\"Photo saved as 'photo.png'\\\")\nelse:\n print(\\\"Failed to capture photo.\\\")\n# Release camera\ncamera.release()\ncv2.destroyAllWindows()\n```\nHope you smiled when I took the pic\nSo I want u to reply to his requests in the above format so that parser can extract the necessary bash and python scripts to execute and fullfill his requests, By the way he is a bit mischievious too. Lol"
                },
                {
                    "role": "user",
                    "content": user_query
                }
            ]
        
        # If we're retrying due to an error, include the error context
        if error_context:
            contents.append(
                {
                    "role": "user",
                    "content": f"The code you provided resulted in an error: {error_context}. Please provide a corrected version."
                }
            )        
        completion = self.client.chat.completions.create(
            model="qwen-2.5-coder-32b",
            messages=contents,
            temperature=0.6,
            max_completion_tokens=1000,
            top_p=0.95,
            stream=True,
            stop=None,
        )

        print("\n[AI is thinking...]")

        response_text = ""
        for chunk in completion:
            print(chunk.choices[0].delta.content or "", end="")
            if chunk.choices[0].delta.content:
                response_text += chunk.choices[0].delta.content
                
        return response_text
    
    def process_query(self, user_query):
        """Process user query, generate AI response, extract and execute code."""
        response_text = self.generate_ai_response(user_query)
        
        # Try up to max_retries times if execution fails
        for attempt in range(self.max_retries):
            # Extract bash and python code
            bash_commands, python_code = self.extract_code_blocks(response_text)
            
            # Execute bash commands if needed
            bash_success, bash_output = self.execute_bash(bash_commands)
            
            # If bash fails, regenerate with error context
            if not bash_success:
                print(f"\n[Attempt {attempt+1}/{self.max_retries}] Bash command failed. Regenerating...")
                response_text = self.generate_ai_response(user_query, bash_output)
                continue
                
            # Execute python code
            script_name = f"test{self.script_counter}.py"
            python_success, python_output = self.execute_python(python_code, script_name)
            print(f"Here is the output:{python_output}")
            # If python execution succeeds, store the script and break the loop
            if python_success:
                # Store the executed script with the query as the key
                self.executed_scripts[user_query] = {
                    "script_name": script_name,
                    "bash_commands": bash_commands,
                    "python_code": python_code,
                    "output": python_output
                }
                self.script_counter += 1
                break
            
            # If python fails and we haven't reached max retries, regenerate with error context
            if attempt < self.max_retries - 1:
                print(f"\n[Attempt {attempt+1}/{self.max_retries}] Python execution failed. Regenerating...")
                response_text = self.generate_ai_response(user_query, python_output)
            else:
                print(f"\n[Failed after {self.max_retries} attempts] Sorry, couldn't complete the task.")
                
        return bash_success and python_success
    
    def run_cli(self):
        """Run the command-line interface in a loop."""
        print("=== AI Command Executor ===")
        print("Type 'exit' or 'quit' to end the program.")
        
        while True:
            print("\n" + "="*50)
            user_query = input("\nWhat would you like Grandpa to ask? > ")
            
            if user_query.lower() in ['exit', 'quit']:
                print("Exiting program. Goodbye!")
                break
                
            success = self.process_query(user_query)
            
            if success:
                print("\n[Task completed successfully]")
            else:
                print("\n[Task could not be completed after multiple attempts]")
                
    def get_executed_scripts(self):
        """Return the dictionary of executed scripts."""
        return self.executed_scripts

# Main execution
if __name__ == "__main__":
    executor = AICommandExecutor()
    executor.run_cli()