from fastapi import APIRouter, Request, Header, HTTPException, status
from fastapi.responses import JSONResponse
from google.oauth2 import id_token
from google.oauth2.credentials import Credentials
from google.auth.transport import requests
from googleapiclient.discovery import build
import base64
import json
import os

from ..CredentialsManager import CredentialsManager
from ..mail import (
    get_unprocessed_emails,
    is_likely_unimportant,
    get_ai_draft,
    publish_draft,
    Email
)
from ..dependencies import (
    db_manager,
    client,
    WEB_CLIENT_ID,
    INTERNAL_TASK_SECRET,
    GCP_PUBSUB_TOPIC,
)

router = APIRouter()

# --- Business Logic Functions ---

async def _login_or_register_user(token: dict) -> tuple[str, str, bool]:
    """
    Handles user registration or login, returning a message, id_token, and a flag indicating if the user is new.
    """
    idinfo = id_token.verify_oauth2_token(token['id_token'], requests.Request(), WEB_CLIENT_ID)

    user_email = idinfo.get('email')
    if not user_email:
        raise ValueError("Email not found in token.")

    # Check if user already exists
    if db_manager.user_exists(user_email):
        return f"User {user_email} now logged in.", token['id_token'], False

    # If user is new, create them
    user_name = idinfo.get('name', 'N/A')
    refresh_token = token.get('refresh_token')
    
    creds = Credentials(token=token['access_token'], refresh_token=refresh_token)
    service = build('gmail', 'v1', credentials=creds)
    profile = service.users().getProfile(userId='me').execute()
    initial_history_id = profile.get('historyId')

    db_manager.insert_new_user(
        name=user_name,
        user_email=user_email,
        refresh_token=refresh_token,
        history_id=initial_history_id
    )
    
    # Set up the initial watch for the new user
    _create_gmail_watch(creds)

    return f"User {user_email} successfully registered.", token['id_token'], True
async def _process_emails_for_user(user_email: str):
    """
    Processes all new emails for a given user.
    """
    refresh_token = db_manager.get_attribute(user_email, "encrypted_refresh_token")
    start_history_id = db_manager.get_attribute(user_email, "history_id")

    creds_manager = CredentialsManager(refresh_token=refresh_token)
    emails: list[Email] = get_unprocessed_emails(creds_manager.creds, start_history_id)

    if not emails:
        print(f"LOG: No new emails to process for {user_email}.")
        return

    for email in emails:
        if not email.body or is_likely_unimportant(email):
            continue

        response_body = get_ai_draft(user_email, email, client, db_manager)
        publish_draft(creds_manager.creds, response_body, email.messageID)

    if emails:
        latest_history_id = max(int(email.historyID) for email in emails)
        db_manager.update_historyID(user_email, str(latest_history_id))
    
    print(f"Successfully processed {len(emails)} emails for {user_email}.")

def _create_gmail_watch(creds: Credentials) -> bool:
    """
    Creates a Gmail watch subscription for the authenticated user.
    """
    try:
        service = build('gmail', 'v1', credentials=creds)
        watch_request = {'labelIds': ['INBOX'], 'topicName': GCP_PUBSUB_TOPIC}
        service.users().watch(userId='me', body=watch_request).execute()
        return True
    except Exception as e:
        print(f"FAILED to create watch for user. Error: {e}")
        return False

def _renew_all_user_watches() -> str:
    """
    Iterates through all users and renews their Gmail watch subscription.
    """
    if not GCP_PUBSUB_TOPIC:
        print("FATAL: GCP_PUBSUB_TOPIC_NAME environment variable not set.")
        raise HTTPException(status_code=500, detail="Server is missing GCP_PUBSUB_TOPIC_NAME configuration.")

    users = db_manager.get_all_users_for_watch()
    if not users:
        return "No users found in the database. Nothing to do."

    success_count, failure_count = 0, 0
    for user_email, refresh_token in users:
        if not refresh_token:
            print(f"Skipping {user_email} due to missing refresh token.")
            failure_count += 1
            continue

        creds_manager = CredentialsManager(refresh_token=refresh_token)
        if _create_gmail_watch(creds_manager.creds):
            print(f"Successfully renewed watch for {user_email}.")
            success_count += 1
        else:
            print(f"FAILED to renew watch for {user_email}.")
            failure_count += 1

    return f"Renewal process finished. Success: {success_count}, Failed: {failure_count}."

# --- API Endpoints ---

@router.post("/login")
async def recieve_auth_code(request: Request):
    """
    Exchanges an auth code for tokens, logs in or registers a user, and sets up a watch for new users.
    """
    try:
        token = await CredentialsManager.get_initial_token(request)
        message, id_token_val, _ = await _login_or_register_user(token)
        return JSONResponse(content={"message": message, "id_token": id_token_val}, status_code=200)
    except Exception as e:
        print(f"Login process failed: {e}")
        return JSONResponse(content={"error": f"Login process failed. {e}"}, status_code=400)

@router.post("/processEmails")
async def pub_sub(request: Request):
    """
    Webhook for Pub/Sub to trigger email processing for a user.
    """
    try:
        pub_sub_dict = await request.json()
        message_data = base64.b64decode(pub_sub_dict['message']['data']).decode('utf-8')
        message_json = json.loads(message_data)
        user_email = message_json['emailAddress']

        await _process_emails_for_user(user_email)

        return JSONResponse(content={"success": True}, status_code=200)
    except Exception as e:
        print(f"Error processing pub/sub message: {e}")
        # Return a 200 to prevent Pub/Sub from retrying a failing message indefinitely.
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=200)

@router.post("/tasks/renew-gmail-watch")
async def trigger_renew_watch(x_internal_secret: str = Header(None)):
    """
    A cron job endpoint to renew all Gmail watch requests. Protected by a secret header.
    """
    if not INTERNAL_TASK_SECRET or x_internal_secret != INTERNAL_TASK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing secret token."
        )

    print("Initiating daily renewal of Gmail watch requests...")
    summary = _renew_all_user_watches()
    print(summary)
    return {"status": "success", "message": summary}
