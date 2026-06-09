import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from dotenv import load_dotenv

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
    service = get_drive_service()
    if not service:
        print("Drive service not available. File will not be uploaded.")
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
        
        print(f"File ID: {file.get('id')} uploaded successfully.")
        return file.get('id')
    except Exception as e:
        print(f"An error occurred uploading to Drive: {e}")
        return None

if __name__ == '__main__':
    # Simple test if credentials are set up
    pass
