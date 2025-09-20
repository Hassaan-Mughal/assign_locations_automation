import os
import requests
import shutil
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/drive"]

# ------------------- AUTHENTICATION -------------------
def authenticate():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
        creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build("drive", "v3", credentials=creds)

# ------------------- DRIVE HELPERS -------------------
def get_folder_id(service, folder_name, parent_id=None):
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
    if parent_id:
        query += f" and '{parent_id}' in parents"

    results = service.files().list(q=query, spaces="drive", fields="files(id, name)").execute()
    items = results.get("files", [])

    if items:
        return items[0]["id"]

    file_metadata = {"name": folder_name, "mimeType": "application/vnd.google-apps.folder"}
    if parent_id:
        file_metadata["parents"] = [parent_id]

    folder = service.files().create(body=file_metadata, fields="id").execute()
    return folder.get("id")


def upload_or_update_file(service, folder_id, local_path, file_name):
    query = f"name='{file_name}' and '{folder_id}' in parents"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get("files", [])

    media = MediaFileUpload(local_path, resumable=True)

    if items:
        file_id = items[0]["id"]
        service.files().update(fileId=file_id, media_body=media).execute()
        print(f"✅ Updated: {file_name}")
    else:
        file_metadata = {"name": file_name, "parents": [folder_id]}
        service.files().create(body=file_metadata, media_body=media, fields="id").execute()
        print(f"📤 Uploaded: {file_name}")

# ------------------- DOWNLOAD -------------------
def download_file(url, save_path):
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(save_path, "wb") as f:
            shutil.copyfileobj(response.raw, f)
        print(f"⬇️ Downloaded: {save_path}")
    else:
        print(f"❌ Failed to download {url}")

# ------------------- SYNC FOLDERS -------------------
def sync_folder_to_drive(service, local_folder, drive_parent_id):
    """Recursively upload/update local folder to Drive."""
    for item in os.listdir(local_folder):
        local_path = os.path.join(local_folder, item)
        if os.path.isdir(local_path):
            folder_id = get_folder_id(service, item, drive_parent_id)
            sync_folder_to_drive(service, local_path, folder_id)
        else:
            upload_or_update_file(service, drive_parent_id, local_path, item)

# ------------------- MAIN WORKFLOW -------------------
def process_files(files_to_download, owners):
    service = authenticate()

    # 1. Ensure root folder on Drive
    root_folder_id = get_folder_id(service, "Instructor Files")

    # 2. Prepare local backup directory
    downloads_dir = Path("downloads")
    downloads_dir.mkdir(exist_ok=True)

    # 3. Create all owner folders locally & on Drive
    for owner in owners:
        owner_folder = downloads_dir / owner
        owner_folder.mkdir(exist_ok=True)
        get_folder_id(service, owner, root_folder_id)  # ensure folder on Drive

    # 4. Download files into owner folders
    for file_info in files_to_download:
        owner = file_info["owner"]
        url = file_info["url"]
        file_name = file_info["name"]

        owner_folder = downloads_dir / owner
        local_path = owner_folder / file_name
        if not local_path.exists():  # don’t re-download if already exists
            download_file(url, local_path)

    # 5. Sync local backup folder with Drive
    sync_folder_to_drive(service, str(downloads_dir), root_folder_id)
