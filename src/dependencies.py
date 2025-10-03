import os
from google import genai
from .db_manager import DBManager

# Constants and initialize shared clients in one place.
WEB_CLIENT_ID = "592589126466-flt6lvus63683vern3igrska7sllq2s9.apps.googleusercontent.com"
client = genai.Client(api_key=os.environ["GEMINI_AGENT_EMAIL"])
db_manager = DBManager()
