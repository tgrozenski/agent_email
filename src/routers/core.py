from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from google.oauth2 import id_token
from google.oauth2.credentials import Credentials
from google.auth.transport import requests
from googleapiclient.discovery import build
import base64
import json

from ..CredentialsManager import CredentialsManager
from ..mail import get_unprocessed_emails, is_likely_unimportant, get_ai_draft, publish_draft, Email
from ..dependencies import db_manager, client, WEB_CLIENT_ID

router = APIRouter()

@router.post("/login")
async def recieve_auth_code(request: Request):
    """
    This is the endpoint to exchange the permission code with token to be used by our API
    """
    # get token
    token = await CredentialsManager.get_initial_token(request)

    try:
        idinfo = id_token.verify_oauth2_token(
            token['id_token'], requests.Request(), WEB_CLIENT_ID, clock_skew_in_seconds=10
        )

        user_name = idinfo.get('name', 'N/A')
        user_email = idinfo.get('email')
        refresh_token = token.get('refresh_token')

        creds = Credentials(token=token['access_token'])
        CredentialsManager.creds = creds

        service = build('gmail', 'v1', credentials=creds)
        profile = service.users().getProfile(userId='me').execute()
        initial_history_id = profile.get('historyId')

        # insert new credentials into db, if user already exists nothing will be done
        db_manager.insert_new_user(
            name=user_name,
            user_email=user_email,
            refresh_token=refresh_token,
            historyID=initial_history_id
        )

    except Exception as e:
        print(f"Token verification failed: {e}")
        return JSONResponse(content={"error": f"Token verification failed. {e}"}, status_code=400)

    return JSONResponse(content = {
        "message": f"User {user_email} successfully registered.",
        "id_token": token['id_token']
        }, status_code=200)

@router.post("/processEmails")
async def pub_sub(request: Request):
    """
    An endpoint that is subscribed to the pub/sub topic
    Recieves a pub sub message from google indicating a change in the user's mailbox
    """
    pub_sub_dict = await request.json()

    # The data from pub/sub is base64 encoded and contains the user's email
    message_data = base64.b64decode(pub_sub_dict['message']['data']).decode('utf-8')
    message_json = json.loads(message_data)
    user_email = message_json['emailAddress']

    # get refresh token and historyID from db
    refresh_token = db_manager.get_attribute(user_email, "encrypted_refresh_token")
    start_history_id = db_manager.get_attribute(user_email, "history_id")

    # use gmail api to get emails since last historyID
    creds_manager: CredentialsManager = CredentialsManager(refresh_token=refresh_token)
    emails: list[Email] = get_unprocessed_emails(creds_manager.creds, start_history_id)

    if not emails:
        print("LOG: No new emails to process.")

    for email in emails:
        if not email.body or is_likely_unimportant(email):
            continue

        user_id = db_manager.get_attribute(user_email, "user_id"),
        response_body = get_ai_draft(
            user_id,
            email,
            client,
            db_manager
        )

        publish_draft(creds_manager.creds, response_body, email.messageID)

    # Update the history ID to the latest one from the processed batch
    if emails:
        latest_history_id = max(int(email.historyID) for email in emails)
        db_manager.update_historyID(user_email, str(latest_history_id))
    print(f"Successfully processed {len(emails)} emails.")

    # As per google documentation we must return a 200 ack
    return JSONResponse(content={}, status_code=200)
