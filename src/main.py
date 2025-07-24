import os
from google import genai
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# REMEMBER TO MOVE API KEY AS ENV VAR
# genai.configure(api_key=os.environ["GEMINI_API_KEY"])
client = genai.Client(api_key="AIzaSyDKM9mHNrc67I-MDukzRpgEmNaqQFqo1Lc")

# Create the FastAPI app
app = FastAPI()

def get_text_content(prompt) -> str:
    # Generating text content using the Gemini model
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
    )
    return response.text

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
            return JSONResponse(content={"error": "Prompt not found in request body"}, status_code=400)

        # Send the prompt to the Gemini API
        response = get_text_content(prompt)

        # Return the Gemini API's response
        return JSONResponse(content={"response": response})

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/")
def read_root():
    return {"message": "Webhook is running. Send a POST request to /webhook with a 'prompt' in the JSON body."}