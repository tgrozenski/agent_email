import os
import json
import base64
from dataclasses import dataclass
import DBMangager
import pg8000.dbapi
from fastapi.middleware.cors import CORSMiddleware
from google.oauth2 import id_token
from google.oauth2.credentials import Credentials
from google.auth.transport import requests
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google import genai
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

WEB_CLIENT_ID = "592589126466-flt6lvus63683vern3igrska7sllq2s9.apps.googleusercontent.com"
AIVEN_PASSWORD = os.environ["AIVEN_PASSWORD"]

# Configure the Gemini client with the API key from environment variables
client = genai.Client(api_key=os.environ["GEMINI_AGENT_EMAIL"])
db_manager = DBMangager()

# Create the FastAPI app
app = FastAPI()

origins = [
    "https://tgrozenski.github.io",
    "http://localhost",
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods
    allow_headers=["*"], # Allows all headers
)


def get_text_content(prompt: str) -> str:
    """Generates text content using the Gemini model."""
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
    )
    return response.text


@app.post("/webhook")
async def webhook(request: Request):
    """
    This endpoint receives a POST request with a JSON payload,
    sends the "prompt" from the payload to the Gemini API,
    and returns the Gemini API's response.
    """
    try:
        data = await request.json()
        prompt = data.get("prompt")

        if not prompt:
            return JSONResponse(content={"error": "Prompt not found in request body"}, status_code=400)

        # Send the prompt to the Gemini API
        response = get_text_content(prompt)

        # Return the Gemini API's response
        return JSONResponse(content={"response": response})

    except Exception as e:
        return JSONResponse(content={"error": "An internal server error occurred."}, status_code=500)


"""
This is the endpoint to exchange the permission code with token to be used by our API
Note: requires running frontend and backend simultaneously on localhost
"""
@app.post("/register")
async def recieve_auth_code(request: Request):

    # get token
    token = await get_initial_token(request)

    # access token
    try:
        idinfo = id_token.verify_oauth2_token(
            token['id_token'], requests.Request(), WEB_CLIENT_ID
        )
        
        user_name = idinfo.get('name', 'N\A')
        user_email = idinfo.get('email')
        refresh_token = token.get('refresh_token')

        # insert new credentials into db
        db_manager.insert_new_user(user_name, user_email, refresh_token)
        

    except Exception as e:
        return JSONResponse(content={"error": f"Token verification failed. {e}"}, status_code=400)

    return {"message": f"User {user_email} successfully registered."}

@dataclass(frozen=True)
class Email:
    header : str
    body : str
    messageID : str
    historyID : str

def get_unprocessed_emails(access_token: str, start_history_id: str) -> list[Email]:
    """
    Uses the Gmail API to find and retrieve all emails received since the last known history ID.
    """
    creds = Credentials(token=access_token)
    service = build('gmail', 'v1', credentials=creds)

    try:
        # Get the history of changes since the last known historyId
        history = service.users().history().list(userId='me', startHistoryId=start_history_id).execute()

        messages_added = []
        if 'history' in history:
            for h in history['history']:
                if 'messagesAdded' in h:
                    # We only care about new messages that are unread and in the inbox
                    for added_msg in h['messagesAdded']:
                        if 'INBOX' in added_msg['message']['labelIds'] and 'UNREAD' in added_msg['message']['labelIds']:
                            messages_added.append(added_msg)

        emails = []
        if not messages_added:
            return emails

        # Fetch each new message
        for added_msg in messages_added:
            msg_id = added_msg['message']['id']
            message = service.users().messages().get(userId='me', id=msg_id, format='full').execute()

            payload = message['payload']
            headers = payload['headers']
            
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
            
            header_info = f"Subject: {subject}\nFrom: {sender}"
            
            body = ""
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain':
                        body_data = part['body'].get('data')
                        if body_data:
                            body = base64.urlsafe_b64decode(body_data).decode('utf-8')
                        break
            else:
                body_data = payload['body'].get('data')
                if body_data:
                    body = base64.urlsafe_b64decode(body_data).decode('utf-8')

            email = Email(
                header=header_info,
                body=body,
                messageID=msg_id,
                historyID=message['historyId']
            )
            emails.append(email)

        return emails

    except Exception as e:
        # Handle potential API errors, e.g., token expiration, permission issues
        print(f"An error occurred while fetching emails: {e}")
        return []


def publish_draft(access_token, draft_body, message_id):
    ...

def get_response_body(email: Email):
    return "Hello world this is a test reply from gemini"


"""
An endpoint that is subscribed to the pub/sub topic
Responsible to
    - get short lived access token from refresh token (for gmail api)
    - determine emails since last historyID
    - process those emails
    - query gemini api for response
    - write draft with gmail api
    - update last historyID in DB
"""
@app.post("/processEmail")
async def pub_sub(request: Request):

    pub_sub_dict = await request.json()
    
    # The data from pub/sub is base64 encoded and contains the user's email
    message_data = base64.b64decode(pub_sub_dict['message']['data']).decode('utf-8')
    message_json = json.loads(message_data)
    user_email = message_json['emailAddress']

    refresh_token = db_manager.get_refresh_token(user_email)
    access_token = get_access_token(refresh_token)
    start_history_id = db_manager.get_history_id(user_email)

    emails: list = get_unprocessed_emails(access_token, start_history_id)

    if not emails:
        return {"message": "No new emails to process."}

    for email in emails:
        response_body = get_response_body(email)
        publish_draft(access_token, response_body, email.messageID)
    
    # Update the history ID to the latest one from the processed batch
    latest_history_id = max(int(email.historyID) for email in emails)
    db_manager.update_historyID(user_email, str(latest_history_id))

    return {"message": f"Successfully processed {len(emails)} emails."}


@app.get("/")
def read_root():
    return {"message": "Webhook is running. Send a POST request to /webhook with a 'prompt' in the JSON body."}

"""
This function will take a refresh token and exchange it for a short
lived access token necessary for using the gmail api
"""
def get_access_token(refresh_token: str) -> str:
    with open('AgentEmailWebClientSecrets.json', 'r') as f:
        client_secrets = json.load(f)['web']

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_secrets['client_id'],
        client_secret=client_secrets['client_secret'],
        scopes=[
            "https://www.googleapis.com/auth/userinfo.email",
            "https://mail.google.com/",
            "https://www.googleapis.com/auth/gmail.compose"
        ]
    )

    creds.refresh(Request())
    return creds.token


async def get_initial_token(request: Request) -> dict:
    flow: Flow = Flow.from_client_secrets_file(
        'AgentEmailWebClientSecrets.json',
        scopes=[
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://mail.google.com/",
            "https://www.googleapis.com/auth/gmail.compose"
        ]
    )
    flow.redirect_uri = 'https://tgrozenski.github.io/agent_email_frontend.github.io/callback.html'

    auth_code = await request.json()
    return flow.fetch_token(code=auth_code['code'])