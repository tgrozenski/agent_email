import unittest
import sys
import os
import os.path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.mail import Email, get_unprocessed_emails
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
                    print(f"  - Subject: {email.header}")
            
            # Update the database with the latest history ID for the next run
            print(f"Updating historyId in DB to {latest_history_id}...")
            update_success = self.db_manager.update_historyID(user_email, latest_history_id)
            self.assertTrue(update_success, "Failed to update historyId in the database.")

        except HttpError as error:
            self.fail(f"An error occurred with the Gmail API: {error}")

if __name__ == "__main__":
    unittest.main()