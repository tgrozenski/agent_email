import os
import logging
from google import genai
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure the Gemini client with the API key from environment variables
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# Create the FastAPI app
app = FastAPI()

def get_text_content(prompt: str) -> str:
    """Generates text content using the Gemini model."""
    logger.info(f"Generating content for prompt: {prompt[:30]}...")
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        logger.info("Successfully generated content from Gemini.")
        return response.text
    except Exception as e:
        logger.error(f"Error generating content from Gemini: {e}")
        raise

@app.post("/webhook")
async def webhook(request: Request):
    """
    This endpoint receives a POST request with a JSON payload,
    sends the "prompt" from the payload to the Gemini API,
    and returns the Gemini API's response.
    """
    try:
        data = await request.json()
        prompt = data.get("prompt")

        if not prompt:
            logger.warning("Prompt not found in request body")
            return JSONResponse(content={"error": "Prompt not found in request body"}, status_code=400)

        # Send the prompt to the Gemini API
        response = get_text_content(prompt)

        # Return the Gemini API's response
        logger.info("Webhook processed successfully.")
        return JSONResponse(content={"response": response})

    except Exception as e:
        logger.error(f"An error occurred in the webhook: {e}")
        return JSONResponse(content={"error": "An internal server error occurred."}, status_code=500)

@app.get("/")
def read_root():
    return {"message": "Webhook is running. Send a POST request to /webhook with a 'prompt' in the JSON body."}
