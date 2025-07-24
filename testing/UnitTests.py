import unittest
import subprocess
import time
import json
import urllib.request
import os

class TestWebhook(unittest.TestCase):
    logging = True

    def setUp(self):
        """Set up the test environment by starting the webhook server."""
        self.server_process = subprocess.Popen(
            ["uvicorn", "src.main:app", "--host", "127.0.0.1", "--port", "8000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        # Give the server a moment to start up
        time.sleep(5)

    def tearDown(self):
        """Tear down the test environment by terminating the webhook server."""
        self.server_process.terminate()
        self.server_process.wait()

    def test_webhook_non_empty_response(self):
        """Test that the webhook returns a non-empty response."""
        url = "http://127.0.0.1:8000/webhook"
        data = {"prompt": "Hello world this is a test prompt."}
        headers = {"Content-Type": "application/json"}

        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers, method='POST')
        
        with urllib.request.urlopen(req) as response:
            self.assertEqual(response.status, 200)
            response_data = json.loads(response.read().decode('utf-8'))
            if self.logging:
                print("LOG: ", response_data)
            self.assertIn("response", response_data)
            self.assertTrue(response_data["response"])

if __name__ == "__main__":
    unittest.main()