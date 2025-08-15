import unittest
from unittest.mock import patch, MagicMock
import subprocess
import time
import json
import urllib.request
import os
from fastapi.testclient import TestClient
import webbrowser

# Add src to path to allow for imports
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.main import app, get_text_content, insert_new_user

class TestGetTextContent(unittest.TestCase):

    @patch('src.main.client')
    def test_get_text_content_success(self, mock_client):
        """Test successful content generation."""
        # Configure the mock to return a successful response
        mock_response = MagicMock()
        mock_response.text = "This is a test response."
        mock_client.models.generate_content.return_value = mock_response

        # Call the function with a test prompt
        prompt = "Test prompt"
        result = get_text_content(prompt)

        # Assert the result
        self.assertEqual(result, "This is a test response.")
        mock_client.models.generate_content.assert_called_once_with(
            model="gemini-2.0-flash",
            contents=prompt,
        )

    @patch('src.main.client')
    def test_get_text_content_api_error(self, mock_client):
        """Test handling of an API error."""
        # Configure the mock to raise an exception
        mock_client.models.generate_content.side_effect = Exception("API Error")

        # Assert that the exception is raised
        with self.assertRaises(Exception) as context:
            get_text_content("Test prompt")
        
        self.assertTrue("API Error" in str(context.exception))


class TestWebhookUnit(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    @patch('src.main.get_text_content')
    def test_webhook_success(self, mock_get_text):
        """Test the webhook endpoint successfully."""
        # Configure the mock to return a successful response
        mock_get_text.return_value = "Mocked Gemini Response"

        # Make a request to the test client
        response = self.client.post("/webhook", json={"prompt": "A test prompt"})

        # Assert the response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"response": "Mocked Gemini Response"})
        mock_get_text.assert_called_once_with("A test prompt")

    def test_webhook_no_prompt(self):
        """Test the webhook endpoint when no prompt is provided."""
        response = self.client.post("/webhook", json={"wrong_key": "some_value"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "Prompt not found in request body"})

    @patch('src.main.get_text_content')
    def test_webhook_internal_error(self, mock_get_text):
        """Test the webhook endpoint when an internal error occurs."""
        # Configure the mock to raise an exception
        mock_get_text.side_effect = Exception("Internal Error")

        response = self.client.post("/webhook", json={"prompt": "A test prompt"})

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"error": "An internal server error occurred."})

class TestInsertNewUser(unittest.TestCase):

    @patch('src.main.pg8000.dbapi.connect')
    def test_insert_new_user_success(self, mock_connect):
        """Test successful user insertion."""
        # Arrange
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        user_name = "Test User"
        user_email = "test@example.com"
        refresh_token = "test_refresh_token"

        # Act
        response = insert_new_user(user_name, user_email, refresh_token)

        # Assert
        self.assertIsNone(response)
        mock_connect.assert_called_once()
        mock_conn.cursor.assert_called_once()
        mock_cursor.execute.assert_called_once_with(
            'INSERT INTO "user" (name, email, encrypted_refresh_token) '
            'VALUES (%s, %s, %s) '
            'ON CONFLICT (email) DO NOTHING',
            (user_name, user_email, refresh_token)
        )
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()

    def test_insert_new_user_no_email(self):
        """Test insertion with no email."""
        response = insert_new_user("Test User", None, "test_token")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(json.loads(response.body), {"error": "user_email or refresh_token are None."})

    def test_insert_new_user_no_token(self):
        """Test insertion with no refresh token."""
        response = insert_new_user("Test User", "test@example.com", None)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(json.loads(response.body), {"error": "user_email or refresh_token are None."})

    @patch('src.main.pg8000.dbapi.connect')
    def test_insert_new_user_db_error(self, mock_connect):
        """Test handling of a database error during connect."""
        # Arrange
        mock_connect.side_effect = Exception("DB Connection Error")

        # Act
        response = insert_new_user("Test User", "test@example.com", "test_token")

        # Assert
        self.assertEqual(response.status_code, 500)
        self.assertEqual(json.loads(response.body), {"error": "Database operation failed."})

    @patch('src.main.pg8000.dbapi.connect')
    def test_insert_new_user_db_execute_error(self, mock_connect):
        """Test handling of a database error during execute."""
        # Arrange
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("DB Execute Error")

        # Act
        response = insert_new_user("Test User", "test@example.com", "test_token")

        # Assert
        self.assertEqual(response.status_code, 500)
        self.assertEqual(json.loads(response.body), {"error": "Database operation failed."})
        mock_conn.close.assert_called_once() # ensure connection is closed even on error

if __name__ == "__main__":
    unittest.main()
