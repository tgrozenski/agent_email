import unittest
from unittest.mock import patch, MagicMock
import subprocess
import time
import json
import urllib.request
import os
from fastapi.testclient import TestClient

# Add src to path to allow for imports
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.main import app, get_text_content


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


if __name__ == "__main__":
    unittest.main()
