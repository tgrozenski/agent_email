
import requests
import base64
import json

# The email address of the user to simulate the Pub/Sub message for
USER_EMAIL = "tyler.grozenski@gmail.com"

# The URL of the locally running FastAPI application
ENDPOINT_URL = "http://localhost:8000/processEmails"

def simulate_pubsub_message():
    """
    Constructs and sends a mock Pub/Sub message to the /processEmails endpoint.
    """
    print(f"Simulating Pub/Sub message for: {USER_EMAIL}")

    # 1. Create the inner message data payload
    message_data = {
        "emailAddress": USER_EMAIL
    }
    message_data_str = json.dumps(message_data)
    
    # 2. Base64-encode the payload (as bytes)
    encoded_data = base64.b64encode(message_data_str.encode('utf-8')).decode('utf-8')

    # 3. Construct the full Pub/Sub message
    pubsub_message = {
        "message": {
            "data": encoded_data,
            "messageId": "simulated-message-12345",
            "publishTime": "2025-09-27T10:00:00.000Z" # Example timestamp
        },
        "subscription": "projects/your-gcp-project/subscriptions/your-subscription-name"
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        # 4. Send the POST request to the endpoint
        response = requests.post(ENDPOINT_URL, json=pubsub_message, headers=headers)

        # 5. Print the response from the server
        print(f"Request sent to {ENDPOINT_URL}")
        print(f"Status Code: {response.status_code}")
        
        # Try to print JSON response, otherwise print raw text
        try:
            print("Response JSON:", response.json())
        except json.JSONDecodeError:
            print("Response Text:", response.text)

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while sending the request: {e}")
        print("Please ensure your FastAPI server is running and accessible at the specified URL.")

if __name__ == "__main__":
    simulate_pubsub_message()
