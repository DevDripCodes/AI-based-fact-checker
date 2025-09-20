from http.server import BaseHTTPRequestHandler
import json
import os
import requests
from urllib.parse import parse_qs

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        return

    def do_POST(self):
        try:
            # Get request body
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            message = data.get('message')
            if not message:
                self.send_error_response({'error': "Missing 'message'"}, 400)
                return

            # Get API key from environment
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                self.send_error_response({'error': 'API key not configured'}, 500)
                return

            api_url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                "gemini-2.0-flash-exp:generateContent"
            )

            system_instruction = """
            You are an expert fact-checker. Your task is to analyze a given statement for factual accuracy. 

            Please respond in the following JSON format:
            {
                "verdict": "TRUE" | "FALSE" | "MISLEADING" | "UNSUPPORTED",
                "explanation": "Detailed explanation of your analysis",
                "highlights": [
                    {
                        "statement": "specific part to highlight",
                        "reason": "why this part is important"
                    }
                ]
            }

            Base your analysis on verifiable facts and provide clear reasoning.
            """

            payload = {
                "system_instruction": {
                    "parts": [{"text": system_instruction}]
                },
                "contents": [
                    {"role": "user", "parts": [{"text": message}]}
                ],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "temperature": 0.2
                }
            }

            headers = {"Content-Type": "application/json"}
            params = {"key": api_key}

            response = requests.post(
                api_url,
                headers=headers,
                params=params,
                data=json.dumps(payload),
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            candidate = result.get("candidates", [{}])[0]
            parts = candidate.get("content", {}).get("parts", [])
            text = parts[0].get("text", "{}") if parts else "{}"

            try:
                parsed_response = json.loads(text)
                self.send_success_response(parsed_response)
            except json.JSONDecodeError:
                # Fallback response if JSON parsing fails
                fallback_response = {
                    "verdict": "ERROR",
                    "explanation": f"Unable to parse AI response. Raw response: {text[:200]}",
                    "highlights": []
                }
                self.send_success_response(fallback_response)

        except requests.exceptions.RequestException as e:
            self.send_error_response({'error': f'API request failed: {str(e)}'}, 500)
        except Exception as e:
            self.send_error_response({'error': f'Internal server error: {str(e)}'}, 500)

    def do_GET(self):
        self.send_success_response({"status": "API is working"})

    def send_success_response(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def send_error_response(self, data, status_code):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))