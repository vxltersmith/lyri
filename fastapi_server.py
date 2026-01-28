from fastapi import (
    FastAPI,
    UploadFile,
    File,
    BackgroundTasks,
    HTTPException,
    Form,
    Request,
)
from fastapi.responses import FileResponse
import shutil
import os
import uuid
import uvicorn
import logging
import yaml
import argparse
from lyri_core import LyricsVideoGenerator
from fastapi.responses import JSONResponse
from config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import json


def read_json_file(file_path):
    with open(file_path, "r") as file:
        # Step 2: Load the JSON data into a dictionary
        data = json.load(file)
    return data


class TaskManager:
    def __init__(self):
        self.tasks = {}

    def add_task(self, task_id, output_video_path):
        self.tasks[task_id] = {
            "output_file_path": output_video_path,
            "status": "Processing",
        }

    def complete_task(self, task_id, output_video_path):
        self.tasks[task_id]["output_file_path"] = output_video_path
        self.tasks[task_id]["status"] = "Completed"
        logger.info(f"Processing completed: {output_video_path} (Task ID: {task_id})")


class AlignerServer:
    def __init__(self, config):
        self.config = config
        self.generator = LyricsVideoGenerator(self.config)

        self.app = FastAPI()
        self.UPLOAD_DIR = config.input_cache or "input_cache"
        self.OUTPUT_DIR = config.output_cache or "output_cache"
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)

        self.task_manager = TaskManager()  # Dictionary to store task statuses
        self.setup_routes()
        logger.info("Aligner Server initialized")

    def setup_routes(self):
        """Define all API routes"""

        @self.app.get("/")
        async def root():
            return {
                "message": "Aligner Server is running. Use /upload to upload a file."
            }

        @self.app.get("/run/{task_id}")
        async def start_processing(task_id: str, background_tasks: BackgroundTasks):
            """Start processing the uploaded file"""
            if task_id not in self.task_manager.tasks:
                return JSONResponse(
                    status_code=404, content={"message": "Task ID not found"}
                )

            task_info = self.task_manager.tasks[task_id]
            if task_info["status"] != "Uploaded":
                return JSONResponse(
                    status_code=400,
                    content={"message": "File is not in 'Uploaded' status"},
                )

            # Process file in the background
            background_tasks.add_task(self.process_file, task_id)

            task_info["status"] = "Processing"
            logger.info(f"Processing started for task ID: {task_id}")

            return {"task_id": task_id, "message": "Processing started"}

        @self.app.post("/upload-meta/{task_id}")
        async def receive_metadata(task_id: str, request: Request):
            task = self.task_manager.tasks.get(task_id)
            if task is None:
                raise HTTPException(status_code=404, detail="Task not found")
            json_data = await request.json()
            task["input_files"]["meta"] = json.loads(json_data)
            logging.info(f"Received metadata for task {task_id}: {json_data}")
            # Process the JSON data as needed
            return JSONResponse(
                content={"status": "success", "received_data": json_data}
            )

        @self.app.post("/upload/")
        async def upload_files(
            task_id: str = Form(None),
            files: list[UploadFile] = File(...),
            keys: list[str] = Form(...),
        ):
            """Upload multiple files and associate them with a task using keys"""
            if not task_id:
                task_id = str(uuid.uuid4())  # Generate a unique task ID if not provided

            if task_id not in self.task_manager.tasks:
                self.task_manager.tasks[task_id] = {
                    "status": "Uploaded",
                    "input_files": {},
                    "output_file_path": None,
                }

            task_info = self.task_manager.tasks[task_id]

            if len(files) != len(keys):
                return JSONResponse(
                    status_code=400,
                    content={"message": "Number of files and keys must match"},
                )

            for file, key in zip(files, keys):
                input_file_path = os.path.join(self.UPLOAD_DIR, file.filename)

                # Save file
                with open(input_file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)

                # Store file info with key
                task_info["input_files"][key] = file.filename

                logger.info(
                    f"File uploaded: {input_file_path} (Task ID: {task_id}, Key: {key})"
                )

            return {"task_id": task_id, "message": "Files uploaded"}

        @self.app.get("/status/{task_id}")
        async def check_status(task_id: str):
            """Check the processing status of a task"""
            task = self.task_manager.tasks.get(task_id)
            if task is None:
                raise HTTPException(status_code=404, detail="Task not found")
            return {"task_id": task_id, "status": task["status"]}

        @self.app.get("/download_file/{task_id}/{file_type}")
        async def download_file(task_id: str, file_type: str):
            task = self.task_manager.tasks.get(task_id)
            if not task or task["status"] != "Completed":
                raise HTTPException(status_code=404, detail="Task not completed")
            results = task["results"]

            if file_type in results.keys():
                file_path = results[file_type]
            else:
                raise HTTPException(status_code=400, detail="Invalid file type")

            if not os.path.exists(file_path):
                raise HTTPException(status_code=404, detail="File not found")

            return FileResponse(
                file_path,
                media_type="application/octet-stream",
                filename=os.path.basename(file_path),
            )

        @self.app.post("/download_all/{task_id}")
        async def download_all(task_id: str):
            task = self.task_manager.tasks.get(task_id)
            if not task or task["status"] != "Completed":
                raise HTTPException(status_code=404, detail="Task not completed")
            results = task["results"]
            files = []
            for key, value in zip(results.keys(), results.values()):
                files.append({"file_type": key, "file_path": value})
            return files

        @self.app.get("/list_tasks")
        async def list_tasks():
            """List all tasks"""
            return self.task_manager.tasks.keys()

        @self.app.delete("/delete/{task_id}")
        async def delete_task(task_id: str):
            """Delete task and remove associated files"""
            task = self.task_manager.tasks.pop(task_id, None)
            if task is None:
                raise HTTPException(status_code=404, detail="Task not found")
            return {"task_id": task_id, "message": "Task deleted successfully"}

    def process_file(self, task_id: str):
        """Process the uploaded file asynchronously"""
        task = self.task_manager.tasks.get(task_id)
        if not task:
            return

        try:
            data = task["input_files"]
            input_file_path = data["audio"]
            background = data["background"]
            data = data["meta"]
            data["audio_file_name"] = input_file_path
            data["background_file_name"] = background

            self.task_manager.tasks[task_id]["status"] = "Processing"
            logger.info(
                f"Processing started for {input_file_path} (Task ID: {task_id})"
            )

            task_config = Config(None, None)
            task_config.from_user_data(data)
            result = self.generator.generate(task_config)
            logger.info("Pipeline completed")

            output_video_path = result.get("video_path")
            sync_file_path = result.get("subtitles_path")
            vocal_audio_full_path = result.get("vocal_path")
            instrumental_audio_full_path = result.get("instrumental_path")
            input_audio_path = result.get("audio_path")

            logger.info("Processing completed")
            self.task_manager.tasks[task_id]["results"] = {}
            results = self.task_manager.tasks[task_id]["results"]
            if sync_file_path:
                results["sync_file_path"] = sync_file_path
                logger.info(f"Artifact: {sync_file_path} (Task ID: {task_id})")
            if output_video_path:
                results["video_file_path"] = output_video_path
                logger.info(f"Artifact: {output_video_path} (Task ID: {task_id})")
            if vocal_audio_full_path:
                results["vocal_audio_full_path"] = vocal_audio_full_path
                logger.info(f"Artifact: {vocal_audio_full_path} (Task ID: {task_id})")
            if instrumental_audio_full_path:
                results["instrumental_audio_full_path"] = instrumental_audio_full_path
                logger.info(
                    f"Artifact: {instrumental_audio_full_path} (Task ID: {task_id})"
                )
            if input_audio_path:
                results["input_audio_path"] = input_audio_path
                logger.info(f"Artifact: {input_audio_path} (Task ID: {task_id})")
            if not any(results.values()):
                raise Exception("Processing failed: No output artifacts generated")
            self.task_manager.tasks[task_id]["status"] = "Completed"
        except Exception as e:
            self.task_manager.tasks[task_id]["status"] = "Failed"
            logger.error(f"Processing failed for {task_id}: {str(e)}")

    def run(self):
        """Start the FastAPI server"""
        uvicorn.run(self.app, host="0.0.0.0", port=8000, log_level="info")


def load_settings(config_path):
    """Load settings from YAML file"""
    try:
        with open(config_path, "r") as file:
            return yaml.safe_load(file)
    except Exception as e:
        logger.error(f"Error loading config: {str(e)}")
        return {}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="API server of Lyri")
    parser.add_argument(
        "--config",
        type=str,
        default="./configs/server_default.yaml",
        help="Path to the configuration file",
    )
    args = parser.parse_args()

    config_dict = load_settings(args.config)
    config = Config(
        config_dict.get("paths", {}).get("input_cache", "input_cache"),
        config_dict.get("paths", {}).get("output_cache", "output_cache"),
    )

    server = AlignerServer(config)
    server.run()
