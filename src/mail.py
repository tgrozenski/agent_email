from dataclasses import dataclass
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import base64

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