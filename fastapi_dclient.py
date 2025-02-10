import requests
import time
import json
import os
import asyncio
import logging

class VideoAlignerClient:
    def __init__(self, api_url="http://127.0.0.1:8000"):
        self.api_url = api_url
        self.logger = logging.getLogger(__name__)

    def upload_files(self, file_paths, keys):
        """Uploads multiple files to the FastAPI server."""
        url = f"{self.api_url}/upload/"
        files = [('files', (os.path.basename(file_path), open(file_path, 'rb'))) for file_path in file_paths]
        data = {'keys': keys}
        response = requests.post(url, files=files, data=data)
        return response.json()
    
    def upload_metadata(self, task_id, metadata):
        """Uploads metadata for a specific task."""
        url = f"{self.api_url}/upload-meta/{task_id}"
        response = requests.post(url, json=metadata)
        return response.json()

    def check_status(self, task_id):
        """Checks the processing status of a task."""
        url = f"{self.api_url}/status/{task_id}"
        response = requests.get(url)
        return response.json()

    def run_task(self, task_id):
        """Starts processing the uploaded files."""
        url = f"{self.api_url}/run/{task_id}"
        response = requests.get(url)
        return response.json()

    def download_file(self, task_id, file_type, output_path):
        """Downloads a specific file type for a task."""
        url = f"{self.api_url}/download_file/{task_id}/{file_type}"
        response = requests.get(url, stream=True)

        if response.status_code == 200:
            with open(output_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
            return f"Downloaded {file_type} successfully to {output_path}"
        else:
            return response.json()

    def download_all(self, task_id):
        """Downloads all available artifacts for a task."""
        url = f"{self.api_url}/download_all/{task_id}"
        response = requests.post(url)
        if response.status_code == 200:
            files = response.json()
            for file in files:
                file_type = file["file_type"]
                file_path = file["file_path"]
                filename = os.path.basename(file_path)
                output_path = f"output_{filename}"
                download_message = self.download_file(task_id, file_type, output_path)
                print(download_message)
        else:
            print("Failed to download all files:", response.json())

    def delete_task(self, task_id):
        """Deletes a task from the server."""
        url = f"{self.api_url}/delete/{task_id}"
        response = requests.delete(url)
        return response.json()

    async def align(self, audio_file_path, meta_data, background_file_path):

        file_paths = [audio_file_path, background_file_path]
        keys = ["audio", "background"]

        self.logger.info("Uploading files...")
        upload_response = self.upload_files(file_paths, keys)
        self.logger.info("Response: %s", upload_response)

        if "task_id" not in upload_response:
            self.logger.error("Error: Task ID not received.")
            return

        task_id = upload_response["task_id"]
        self.logger.info(f"Task ID: {task_id}")
        
        # Convert the dictionary to a JSON string
        self.logger.info("Uploading metadata...")
        json_data = json.dumps(meta_data, indent=4)
        upload_response = self.upload_metadata(task_id, json_data)
        self.logger.info("Response: %s", upload_response)

        # Start processing
        self.logger.info("Starting processing...")
        run_response = self.run_task(task_id)
        self.logger.info("Response: %s", run_response)

        # Check status until processing is done
        while True:
            self.logger.info("Checking status...")
            status_response = self.check_status(task_id)
            self.logger.info("Status: %s", status_response)

            if status_response["status"] in ["Completed", "Failed"]:
                break

            await asyncio.sleep(5)  # Wait before checking again

        if status_response["status"] == "Completed":
            self.logger.info("Downloading all processed files...")
            self.download_all(task_id)

        # Clean up by deleting the task
        self.logger.info("Deleting task...")
        delete_response = self.delete_task(task_id)
        self.logger.info("Response: %s", delete_response)

# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    client = VideoAlignerClient()

    audio_file_path = "./data/inputs_cache/video_f8967262-d249-4de4-b6fe-cf7b80a2753f.mp4.wav"
    metaconfig_file_path = "./data/inputs_cache/sample.json"
    background_file_path = "./data/inputs_cache/video_f8967262-d249-4de4-b6fe-cf7b80a2753f.mp4"
    production_type = "music"
    meta_data = {
        'production_type': production_type,
        'aspect_ratio': 'vertical',
        'video_resolution': (1920, 1080)
    }

    asyncio.run(client.align(audio_file_path, meta_data, background_file_path))