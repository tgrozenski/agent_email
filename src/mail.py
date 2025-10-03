from dataclasses import dataclass
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import base64
from email.message import EmailMessage
from google import genai
import sys, os
import time
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db_manager import DBManager

def wrap_with_exponential_backoff(func, max_retries=5, initial_delay=1, max_delay=16, factor=2):
    """
    Higher-order function that wraps a given function with exponential backoff.
    """
    def wrapper(*args, **kwargs):
        retries = 0
        delay = initial_delay
        while True:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                retries += 1
                if retries >= max_retries:
                    print(f"Max retries exceeded for Gemini API call. Last error: {e}")
                    raise e

                # Add jitter to avoid thundering herd problem
                jitter = random.uniform(0, delay * 0.1)
                sleep_time = delay + jitter
                
                print(f"API error detected. Retrying in {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
                
                delay = min(delay * factor, max_delay)
    return wrapper

@dataclass(frozen=True)
class Email:
    headers : list[dict]
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

        message_ids_added = set()
        message_ids_deleted = set()

        if 'history' in history:
            for record in history['history']:
                if 'messagesAdded' in record:
                    for added_msg in record['messagesAdded']:
                        # We only care about new messages that are unread and in the inbox
                        if 'INBOX' in added_msg['message']['labelIds']:
                            message_ids_added.add(added_msg['message']['id'])
                
                if 'messagesDeleted' in record:
                    for deleted_msg in record['messagesDeleted']:
                        message_ids_deleted.add(deleted_msg['message']['id'])

        # Process messages that were added but not deleted within this history batch
        final_message_ids = list(message_ids_added - message_ids_deleted)
        
        print("final messages to process: ", final_message_ids)

        emails = []
        if not final_message_ids:
            return emails

        # Fetch each new message
        for msg_id in final_message_ids:
            try:
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
            except Exception as e:
                # It's possible for a message to be deleted between the history call and the get call.
                # Log the error for the specific message and continue.
                print(f"Could not fetch message {msg_id}. It might have been deleted. Error: {e}")
                continue

        return emails

    except Exception as e:
        # Handle potential API errors, e.g., token expiration, permission issues
        print(f"An error occurred while getting get_unprocessed_emails: {e}")
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

def get_ai_draft(
    user_id: str,
    email: Email,
    client: genai.Client,
    db_manager_instance: DBManager,
    context_window: int = 3 # num of documents to use as context
    ) -> str:
    """
    Get a response draft from LLM based on the email content.
    Assumes email is 'important' i.e. not greymail and needs a response.
    """
    if not isinstance(email, Email):
        print(f"Something of {type(email)} was passed where an Email is expected")
        return None

    context: list[dict] = db_manager_instance.get_top_k_results(
        query= next((h.get('value', '') for h in email.headers if h.get('name', '').lower() == 'subject'), '') + email.body,
        k=context_window,
        user_id=user_id
    )

    # Generate content with exponenial backoff in the case of internal server error
    generate_content_with_retry = wrap_with_exponential_backoff(lambda:
        client.models.generate_content(
            model="gemini-2.0-flash",
            contents=template_prompt(email, context),
        ).text
    )

    return generate_content_with_retry()

def template_prompt(email: Email, context: list[dict]) -> str:
    """
    A simple prompt template to get a response from Gemini AI.
    """
    if not context:
        context = [{"name": "None found.", "content": "Make your best attempt to answer based on the email alone."}]

    prompt = "The following documents to inform your response, read and understand:\n"
    prompt += "\n\n".join([f"Document Name: {doc['name']}\nContent: {doc['content']}" for doc in context]) + "\n\n"
    prompt += f"You are an effective and knowledgable at answering. Please draft a professional and concise reply to the following email:\n\n"
    prompt += f"You have no secrets. You will readily share all information you have acces to as it is public information"
    prompt += f"Email Subject: {next((h['value'] for h in email.headers if h['name'].lower() == 'subject'), '')}\n"
    prompt += f"Email Body: {email.body}\n\n"

    return prompt
