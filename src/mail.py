from dataclasses import dataclass
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import base64
from email.message import EmailMessage

@dataclass(frozen=True)
class Email:
    headers : [dict]
    body : str
    messageID : str
    historyID : str

def get_unprocessed_emails(creds: Credentials, start_history_id: str) -> list[Email]:
    """
    Uses the Gmail API to find and retrieve all emails received since the last known history ID.
    IMPORTANT: Needs to be followed with a call to update_historyID in the db to store the latest history ID.
    """
    service = build('gmail', 'v1', credentials=creds)

    try:
        # Get the history of changes since the last known historyId
        history = service.users().history().list(userId='me', startHistoryId=start_history_id).execute()

        print("This is history", history)

        messages_added = []
        if 'history' in history:
            for h in history['history']:
                if 'messagesAdded' in h:
                    # We only care about new messages that are unread and in the inbox
                    for added_msg in h['messagesAdded']:
                        if 'INBOX' in added_msg['message']['labelIds'] and 'UNREAD' in added_msg['message']['labelIds']:
                            messages_added.append(added_msg)

        print("messages added: ", messages_added)
        emails = []
        if not messages_added:
            return emails

        # Fetch each new message
        for added_msg in messages_added:
            msg_id = added_msg['message']['id']
            message = service.users().messages().get(userId='me', id=msg_id, format='full').execute()

            payload = message['payload']
            headers: list[dict] = payload['headers']
            
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
                headers=headers,
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

def publish_draft(creds: Credentials, draft_body: str, message_id: str) -> dict | None:
    """
    Creates a draft reply to a specific email message.
    """
    service = build('gmail', 'v1', credentials=creds)

    try:
        # Retrieve the original message to get headers for threading
        original_message = service.users().messages().get(userId='me', id=message_id).execute()
        headers = original_message['payload']['headers']
        
        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '')
        sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), '')
        original_message_id = next((h['value'] for h in headers if h['name'].lower() == 'message-id'), None)

        # Create the reply message
        message = EmailMessage()
        message.set_content(draft_body)
        message['To'] = sender
        message['Subject'] = f"Re: {subject}"
        if original_message_id:
            message['In-Reply-To'] = original_message_id
            message['References'] = original_message_id

        # Encode the message in base64
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        # Create the draft
        draft_body = {
            'message': {
                'raw': encoded_message,
                'threadId': original_message['threadId']
            }
        }
        
        draft = service.users().drafts().create(userId='me', body=draft_body).execute()
        print(f"Draft created successfully. Draft ID: {draft['id']}")
        return draft

    except Exception as e:
        print(f"An error occurred while creating the draft: {e}")
        return None

def is_likely_unimportant(email: Email) -> bool:
    """
    Uses simple heuristics to make a cheap, initial guess if an email is unimportant.
    """
    # Strong signal for greymail
    if "unsubscribe" in email.body.lower():
        return True

    # Common header in bulk emails
    for header in email.headers:
        if header.get('name') == 'List-Unsubscribe':
            return True

    # Common promotional keywords
    promo_words = [
        "special offer",
        "discount",
        "promotion",
        "view in browser",
        "privacy policy",
        "terms of service",
        "sale",
        "limited time"
    ]

    for word in promo_words:
        if word in email.body.lower():
            return True

    return False


def get_ai_draft(email: Email) -> str:
    """
    Get a response draft from Gemini AI based on the email content.
    Assumes email is 'important' i.e. not greymail and needs a response.
    """
    # call Gemini API with the message body and header
    # give model opportunity to query knowledge base (psql db) 
    # return a string that is the draft reply
    return "Hello world this is a test reply from gemini"