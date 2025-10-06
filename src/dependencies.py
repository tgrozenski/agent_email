import os
import json
from google import genai
from .db_manager import DBManager

# configuration
WEB_CLIENT_ID = "592589126466-flt6lvus63683vern3igrska7sllq2s9.apps.googleusercontent.com"
INTERNAL_TASK_SECRET = os.environ.get("INTERNAL_TASK_SECRET")
GCP_PUBSUB_TOPIC = os.environ.get("GCP_PUBSUB_TOPIC_NAME")

# Load the client secrets from the environment variable and parse the JSON string
raw_client_secrets = os.environ.get("GOOGLE_CREDENTIALS")
if not raw_client_secrets:
    raise ValueError("The GOOGLE_CREDENTIALS environment variable is not set or is empty.")
CLIENT_SECRETS = json.loads(raw_client_secrets)

# shared clients
client = genai.Client(api_key=os.environ["GEMINI_AGENT_EMAIL"])
db_manager = DBManager()
