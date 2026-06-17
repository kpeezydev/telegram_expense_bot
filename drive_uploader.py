import os
import time
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from dotenv import load_dotenv

import metrics

logger = logging.getLogger(__name__)

load_dotenv()

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive.file']

SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "credentials.json")
DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")

def get_drive_service():
    """Authenticate and return the Google Drive service."""
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        print(f"Warning: Service account credentials file '{SERVICE_ACCOUNT_FILE}' not found.")
        return None

    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)
        return service
    except Exception as e:
        print(f"Error authenticating with Google Drive: {e}")
        return None

def upload_file_to_drive(file_path: str, file_name: str, mimetype: str = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'):
    """Uploads a file to Google Drive."""
    start = time.monotonic()
    service = get_drive_service()
    if not service:
        logger.warning("Drive service not available. File will not be uploaded.", extra={"duration_ms": round((time.monotonic() - start) * 1000, 2)})
        return None

    try:
        file_metadata = {'name': file_name}
        if DRIVE_FOLDER_ID:
            file_metadata['parents'] = [DRIVE_FOLDER_ID]

        media = MediaFileUpload(file_path, mimetype=mimetype)
        
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        duration = time.monotonic() - start
        logger.info(f"File ID: {file.get('id')} uploaded successfully.", extra={"duration_ms": round(duration * 1000, 2)})
        return file.get('id')
    except Exception as e:
        duration = time.monotonic() - start
        logger.error(f"An error occurred uploading to Drive: {e}", extra={"duration_ms": round(duration * 1000, 2)})
        metrics.bot_errors_total.labels(module="drive_uploader", exception_type=type(e).__name__).inc()
        return None

if __name__ == '__main__':
    # Simple test if credentials are set up
    pass
