import os
import base64
import json
import requests
from dotenv import load_dotenv

load_dotenv()

class VisionGatekeeper:
    def __init__(self, api_key: str, model_name="google/gemini-3.1-flash-lite"):
        self.api_key = api_key
        self.model_name = model_name
        self.url = "https://openrouter.ai/api/v1/chat/completions"

    def _encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def extract_metadata(self, image_path: str) -> dict:
        """
        Uses OpenRouter (Cloud Vision) to extract Artist and Album.
        """
        base64_image = self._encode_image(image_path)
        
        prompt = (
            "Identify the musical artist and the album title from this vinyl cover. "
            "Return the result strictly as a JSON object with the keys 'artist' and 'album'. "
            "Do not include any conversational text or markdown."
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/joachimdemuth/shouldibuythisvinyl",
            "X-Title": "Second Life, Inc"
        }

        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "response_format": { "type": "json_object" }
        }

        try:
            response = requests.post(self.url, headers=headers, json=payload, timeout=30)
            if response.status_code != 200:
                return {"error": f"OpenRouter Error ({response.status_code}): {response.text}"}

            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                content_raw = result['choices'][0]['message']['content']
                
                if "```json" in content_raw:
                    content_raw = content_raw.split("```json")[1].split("```")[0].strip()
                elif "```" in content_raw:
                    content_raw = content_raw.split("```")[1].split("```")[0].strip()
                
                data = json.loads(content_raw)
                if 'artist' in data and 'album' in data:
                    return {
                        "artist": str(data['artist']).strip(),
                        "album": str(data['album']).strip()
                    }
            return {"error": "Failed to parse JSON from model response"}
        except Exception as e:
            return {"error": f"Cloud Vision failed: {str(e)}"}

    def ask_reasoning(self, prompt: str) -> dict:
        """
        Uses OpenRouter (Cloud LLM) for text-based reasoning.
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/joachimdemuth/shouldibuythisvinyl",
            "X-Title": "Second Life, Inc"
        }

        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "response_format": { "type": "json_object" }
        }

        try:
            response = requests.post(self.url, headers=headers, json=payload, timeout=30)
            if response.status_code != 200:
                return {"error": f"OpenRouter Error ({response.status_code}): {response.text}"}

            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                content_raw = result['choices'][0]['message']['content']
                
                if "```json" in content_raw:
                    content_raw = content_raw.split("```json")[1].split("```")[0].strip()
                elif "```" in content_raw:
                    content_raw = content_raw.split("```")[1].split("```")[0].strip()
                
                data = json.loads(content_raw)
                return data
            return {"error": "Failed to parse LLM response"}
        except Exception as e:
            return {"error": f"Reasoning failed: {str(e)}"}
