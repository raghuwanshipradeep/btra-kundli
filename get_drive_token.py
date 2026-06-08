"""One-shot script to (re)authorize Google Drive and write token.json.

Run when Drive uploads fail with 'invalid_grant: Token has been expired or revoked'.
Opens a browser for Google consent, then saves the refresh token to token.json.

Usage:
    python get_drive_token.py
"""
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

from config import settings

# Must match _SCOPES in drive_uploader.py — a scope mismatch invalidates the token.
SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def main() -> None:
    creds_path = settings.google_oauth_credentials_path
    token_path = Path(settings.google_token_path)

    flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
    # access_type=offline + prompt=consent guarantees a *fresh* refresh token is returned;
    # without prompt=consent Google may return only an access token (no refresh token).
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")

    token_path.write_text(creds.to_json())
    print(f"Token saved to {token_path.resolve()}")
    print("Restart the server so the new credentials are picked up.")


if __name__ == "__main__":
    main()
