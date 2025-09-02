import unittest
import sys
import os
import os.path
import base64

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.mail import Email, get_unprocessed_emails, publish_draft, is_likely_unimportant
from src.db_manager import DBManager

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# The scopes needed for the operations in mail.py
SCOPES = ["https://mail.google.com/"]

class TestMailIntegration(unittest.TestCase):
    """
    Integration tests for mail.py.
    Requires user interaction for OAuth on first run.
    Requires the test user to be pre-populated in the database.
    """

    creds = None
    db_manager = None

    @classmethod
    def setUpClass(cls):
        """Handles OAuth flow and DB connection before running tests."""
        cls.db_manager = DBManager()
        token_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'token.json')
        
        if os.path.exists(token_path):
            cls.creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        
        if not cls.creds or not cls.creds.valid:
            if cls.creds and cls.creds.expired and cls.creds.refresh_token:
                cls.creds.refresh(Request())
            else:
                secrets_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'AgentEmailWebClientSecrets.json')
                if not os.path.exists(secrets_file):
                    secrets_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'credentials.json')
                
                if not os.path.exists(secrets_file):
                    raise FileNotFoundError("Could not find 'AgentEmailWebClientSecrets.json' or 'credentials.json' in the project root. Please configure your OAuth client ID.")

                flow = InstalledAppFlow.from_client_secrets_file(secrets_file, SCOPES)
                cls.creds = flow.run_local_server(port=0)
            
            with open(token_path, "w") as token:
                token.write(cls.creds.to_json())

    def get_email_by_id(self, message_id: str) -> Email:
        """Helper to fetch a full email message by its ID."""
        try:
            service = build('gmail', 'v1', credentials=self.creds)
            message = service.users().messages().get(userId='me', id=message_id).execute()

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

            return Email(
                headers=headers,
                body=body,
                messageID=message_id,
                historyID=message['historyId']
            )
        except HttpError as error:
            self.fail(f"An error occurred while fetching the email: {error}")
            return None
    
    def verify_draft(self, original_message_id: str, expected_draft_text: str) -> bool:
        """HELPER, Verifies that a draft with specific text exists in reply to a message."""
        try:
            service = build('gmail', 'v1', credentials=self.creds)

            message = service.users().messages().get(userId='me', id=original_message_id).execute()
            thread_id = message.get('threadId')
            if not thread_id:
                print(f"Could not find threadId for message {original_message_id}")
                return False

            drafts_response = service.users().drafts().list(userId='me').execute()
            drafts = drafts_response.get('drafts', [])

            for draft_item in drafts:
                draft = service.users().drafts().get(userId='me', id=draft_item['id']).execute()
                if draft.get('message', {}).get('threadId') == thread_id:
                    # Found a draft in the right thread, now check content
                    payload = draft['message']['payload']
                    body_data = ""
                    if 'parts' in payload:
                        for part in payload['parts']:
                            if part['mimeType'] == 'text/plain':
                                body_data = part['body'].get('data')
                                break
                    else:
                        body_data = payload['body'].get('data')
                    
                    if body_data:
                        decoded_body = base64.urlsafe_b64decode(body_data).decode('utf-8')
                        if expected_draft_text in decoded_body:
                            print(f"Success: Found matching draft {draft_item['id']} with correct text.")
                            # Clean up the created draft
                            service.users().drafts().delete(userId='me', id=draft_item['id']).execute()
                            print(f"Cleaned up draft {draft_item['id']}.")
                            return True

            print(f"No draft found for thread {thread_id} with the expected text.")
            return False

        except HttpError as error:
            print(f"An error occurred during draft verification: {error}")
            return False

    def test_get_unprocessed_emails_with_db_history(self):
        """Test getting unprocessed emails using historyId from the database."""
        self.assertIsNotNone(self.creds, "Credentials should not be None")
        self.assertTrue(self.creds.valid, "Credentials are not valid")

        try:
            service = build("gmail", "v1", credentials=self.creds)
            
            profile = service.users().getProfile(userId='me').execute()
            user_email = profile.get('emailAddress')
            latest_history_id = profile.get('historyId')

            self.assertIsNotNone(user_email, "Could not get user email from profile.")
            self.assertIsNotNone(latest_history_id, "Could not get latest historyId from profile.")

            # Fetch the old historyId from the database
            start_history_id = self.db_manager.get_attribute(user_email, 'history_id')
            
            self.assertIsNotNone(
                start_history_id, 
                f"History ID not found in DB for user {user_email}. Please pre-populate the user table."
            )

            print(f"\nFetching emails for {user_email} between historyId {start_history_id} and {latest_history_id}...")
            
            emails = get_unprocessed_emails(self.creds, start_history_id)

            print(f"Found {len(emails)} new email(s).")
            self.assertIsInstance(emails, list)
            if emails:
                for email in emails:
                    self.assertIsInstance(email, Email)
            
            # Update the database with the latest history ID for the next run
            print(f"Updating historyId in DB to {latest_history_id}...")
            update_success = self.db_manager.update_historyID(user_email, latest_history_id)
            self.assertTrue(update_success, "Failed to update historyId in the database.")

        except HttpError as error:
            self.fail(f"An error occurred with the Gmail API: {error}")
        
    def test_publish_draft(self):
        """Tests creating a draft and then verifying it."""
        self.assertIsNotNone(self.creds, "Credentials should not be None")
        self.assertTrue(self.creds.valid, "Credentials are not valid")

        # NOTE: This message ID exists in tyler.grozenski@gmail.com's inbox.
        test_message_id = '1990a62f211c5c37' 
        draft_text = "This is the text for the test draft."

        draft_response = publish_draft(self.creds, draft_text, test_message_id)
        self.assertIsNotNone(draft_response, "Failed to create draft.")

        verification_success = self.verify_draft(test_message_id, draft_text)
        self.assertTrue(verification_success, "Draft verification failed.")
    
    def test_is_likely_unimportant(self):
        """Tests the is_likely_unimportant function with various subjects."""
        # These message IDs exist in tyler.grozenski@gmail.com's inbox.
        # All are promotional or bulk emails.
        promo_emails = [
            "19902d25ac67032a",
            "1990319362a4f333",
            "19905aa8b8ca0486",
            "19905c59d89bd038",
            "1990647ea72e66a9"
        ]

        for message_id in promo_emails:
            email: Email = self.get_email_by_id(message_id)
            self.assertTrue(is_likely_unimportant(email))

if __name__ == "__main__":
    unittest.main()