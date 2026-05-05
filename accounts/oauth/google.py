import json
from google.auth.transport import requests
from google.oauth2 import id_token
import requests as httpRequest
import os

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")


class Google:
    """
    this clas fetches user data from goole
    and returns user date in a dictionaary format.
    it also validates the token.
    """

    @staticmethod
    def validate(token):
        try:
            idinfo = id_token.verify_oauth2_token(
                token,
                requests.Request(),
            )

            if idinfo["iss"] not in [
                "accounts.google.com",
                "https://accounts.google.com",
            ]:
                raise ValueError("Wrong issuer.")
            return idinfo

        except Exception as e:
            return "Invalid Token"

    @staticmethod
    def get_id_token(token):
        try:
            token_url = "https://oauth2.googleapis.com/token"
            payload = {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "code": token,
                "redirect_uri": "postmessage",
                "grant_type": "authorization_code",
                "access_type": "offline",
            }

            try:
                # Making a POST request to the token endpoint
                request_data = json.dumps(payload)
                response = httpRequest.post(token_url, data=request_data)
                response.raise_for_status()

                # Extracting the access token from the response
                id_token = response.json()["id_token"]

                return id_token

            except Exception as e:
                return response.text

        except Exception:
            return "Invalid Token"
