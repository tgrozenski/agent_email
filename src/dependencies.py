import os
from google import genai
from .db_manager import DBManager

# configuration
WEB_CLIENT_ID = "592589126466-flt6lvus63683vern3igrska7sllq2s9.apps.googleusercontent.com"
INTERNAL_TASK_SECRET = os.environ.get("INTERNAL_TASK_SECRET")
CLIENT_SECRETS_FILE = os.environ.get("GOOGLE_CLIENT_SECRETS_PATH", "credentials.json")
GCP_PUBSUB_TOPIC = os.environ.get("GCP_PUBSUB_TOPIC_NAME")
SCOPES = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://mail.google.com/",
    "https://www.googleapis.com/auth/gmail.compose"
]

# shared clients
client = genai.Client(api_key=os.environ["GEMINI_AGENT_EMAIL"])
db_manager = DBManager()
