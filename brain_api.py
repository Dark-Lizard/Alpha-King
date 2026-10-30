import os
import requests
import google.generativeai as genai

class BrainAPIHandler:
    def __init__(self, email=None, password=None, gemini_key=None):
        self.email = email
        self.password = password
        self.gemini_key = gemini_key
        self.session = requests.Session()
        self.base_url = "https://api.worldquantbrain.com"
        
        if self.gemini_key:
            genai.configure(api_key=self.gemini_key)

    def authenticate_brain(self):
        """Authenticate with WorldQuant Brain API using Basic Auth."""
        if not self.email or not self.password:
            return False, "Email and Password are required for WorldQuant Brain sync."
        try:
            response = self.session.post(
                f"{self.base_url}/authentication",
                auth=(self.email, self.password),
                timeout=10
            )
            if response.status_code == 200:
                return True, "Successfully authenticated with WorldQuant Brain!"
            else:
                return False, f"Authentication failed: {response.status_code} - {response.text}"
        except Exception as e:
            return False, f"Connection error: {str(e)}"

    def sync_realtime_data(self):
        """Fetches real-time user profile, quota, or active workspace status from Brain."""
        auth_success, msg = self.authenticate_brain()
        if not auth_success:
            return None, msg

        try:
            resp = self.session.get(f"{self.base_url}/users/self", timeout=10)
            if resp.status_code == 200:
                user_data = resp.json()
                return user_data, "Real-time sync completed successfully."
            else:
                return {"status": "Connected", "note": "Authenticated session active."}, "Connected successfully!"
        except Exception as e:
            return None, f"Sync error: {str(e)}"

    def ask_gemini_analysis(self, prompt, context_data):
        """Sends data context to Google Gemini for quantitative analysis."""
        if not self.gemini_key:
            return "Gemini API key not provided."
        try:
            model = genai.GenerativeModel('gemini-1.5-pro')
            response = model.generate_content(f"{prompt}\n\nContext Data:\n{str(context_data)}")
            return response.text
        except Exception as e:
            return f"Gemini generation error: {str(e)}"
