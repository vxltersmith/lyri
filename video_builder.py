import os
import ffmpeg
import logging
from config import Config

class VideoBuilder:
    def __init__(self, config):
        self.config = config
        self.default_background_path = self.config.default_background_path

    def get_audio_duration(self, audio_path):
        """Get the duration of the audio."""
        try:
            probe = ffmpeg.probe(audio_path)
            return float(probe['format']['duration'])
        except ffmpeg.Error as e:
            logging.error(f"Error getting audio duration: {e.stderr.decode()}")
            return 0

    def get_video_frame_rate(self, video_path):
        """Get the frame rate of the video."""
        try:
            probe = ffmpeg.probe(video_path)
            video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
            if video_stream:
                frame_rate = video_stream.get('avg_frame_rate', video_stream.get('r_frame_rate', '24/1'))
                num, den = map(int, frame_rate.split('/'))
                return num / den if den != 0 else 24
            return 24
        except ffmpeg.Error as e:
            logging.warning(f"Warning: Could not determine frame rate, using default. Error: {e.stderr.decode()}")
            return 24

    def strip_audio_from_video(self, video_path, output_path):
        """Strip audio from a video file."""
        try:
            ffmpeg.input(video_path).output(output_path, an=None, vcodec='copy').run()
            logging.info(f"Audio stripped from video: {output_path}")
            return output_path
        except ffmpeg.Error as e:
            logging.error(f"Error stripping audio from video: {e.stderr.decode()}")
            return None

    def build_video(self, sync_file_path, input_audio_path, task_config: Config):
        """Build the final video with the desired size and embed the original video inside it."""
        output_file_path = os.path.join(self.config.output_cache, f"{task_config.audio_file_name}_aligned.mp4")
        background_path = (
            os.path.join(self.config.input_cache, task_config.background_file_name)
            if self.config.background_file_name else self.default_background_path
        )

        frame_rate = self.get_video_frame_rate(background_path)
        duration = self.get_audio_duration(input_audio_path)

        try:
            width, height = self.config.video_resolution  # Desired final size
            aspect_ratio = self.config.aspect_ratio  # 'vertical' or 'horizontal'

            # Process background input (image or video)
            inv = self.prepare_background(background_path, frame_rate, duration)

            # Input audio
            ina = ffmpeg.input(input_audio_path)

            # Scale & pad video to fit inside the final resolution
            vf_filters = self.create_video_filters(width, height, sync_file_path)

            # Add subtitles and overlay text if necessary
            if sync_file_path:
                vf_filters += f",subtitles={sync_file_path}"
            if self.config.overlay_text:
                vf_filters += f",drawtext=text='{self.config.overlay_text}':x=5:y=5:fontcolor=white:fontsize='sqrt(w*h)*0.05'"

            # Explicitly set pixel format and color range
            out = ffmpeg.output(
                inv, ina, output_file_path,
                vf=vf_filters,
                preset="fast",
                pix_fmt="yuv420p",  # Explicit pixel format
                acodec="aac",
                strict="experimental",
                shortest=None,
                t=duration,
                color_range="tv"  # Optionally set color range (e.g., "tv" or "pc")
            ).overwrite_output()

            out.run()
            logging.info(f"Video created successfully: {output_file_path}")
            return output_file_path
        except ffmpeg.Error as e:
            logging.error(f"Error occurred during video creation: {e.stderr.decode()}")
            return None


    def prepare_background(self, background_path, frame_rate, duration):
        """Prepare background video or image for video creation."""
        is_image = background_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff'))
        if is_image:
            return ffmpeg.input(background_path, loop=1, t=duration, framerate=frame_rate)
        else:
            stripped_video_path = background_path + "_background_no_audio.mp4"
            background_path = self.strip_audio_from_video(background_path, stripped_video_path)
            return ffmpeg.input(background_path, stream_loop=-1)

    def create_video_filters(self, width, height, sync_file_path):
        """Create scaling and padding filters for video."""
        scale_filter = f"scale='if(gt(iw/ih,{width}/{height}),{width},-2)':'if(gt(iw/ih,{width}/{height}),-2,{height})'"
        pad_filter = f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black"
        vf_filters = f"{scale_filter},{pad_filter}"
        return vf_filters
