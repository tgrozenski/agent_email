import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request

class CredentialsManager:
    creds: Credentials = None

    def __init__(self, token: dict = None, refresh_token: str = None):
        """
        Builds credentials from either a provided access token or a refresh token.
        """
        print("this is token", token, " this is refresh token: ", refresh_token)
        if not refresh_token and not token:
            raise ValueError("Either token or refresh_token must be provided")
        # If a token is provided, use it directly
        elif token:
            self.creds = Credentials(token=token['access_token'])
        # If a refresh token is provided, build credentials from it
        else:
            with open('credentials.json', 'r') as f:
                client_secrets = json.load(f)['web']

            creds = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_secrets['client_id'],
                client_secret=client_secrets['client_secret'],
                scopes=[
                    "https://www.googleapis.com/auth/userinfo.email",
                    "https://mail.google.com/",
                    "https://www.googleapis.com/auth/gmail.compose"
                ]
            )

            creds.refresh(Request())
            self.creds = creds

    def get_access_token(self) -> str:
        if not self.creds:
            raise ValueError("Credentials must be valid")
        if not self.creds.token:
            self.creds.refresh(Request())
        return self.creds.token

    def get_refresh_token(self) -> str:
        return self.creds.refresh_token

    @staticmethod
    async def get_initial_token(request: Request) -> dict:
        flow: Flow = Flow.from_client_secrets_file(
            'credentials.json',
            scopes=[
                "openid",
                "https://www.googleapis.com/auth/userinfo.email",
                "https://mail.google.com/",
                "https://www.googleapis.com/auth/gmail.compose"
            ]
        )
        flow.redirect_uri = 'https://tgrozenski.github.io/agent_email_frontend.github.io/callback.html'

        auth_code = await request.json()
        return flow.fetch_token(code=auth_code['code'])
