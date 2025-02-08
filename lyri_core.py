import os
import shutil
import ffmpeg
import langid
from io import BytesIO
from aeneas.executetask import ExecuteTask
from aeneas.task import Task
from audio_separator.separator import Separator
import logging
import argparse
from config import Config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class AudioProcessor:
    def __init__(self, config):
        self.config = config
        self.audio_cache_path = os.path.join(self.config.input_cache, 'audio_cache')
        vocal_separator = Separator(
            output_dir=self.audio_cache_path,
            model_file_dir=os.path.dirname(self.config.vocal_separator_model),
        )
        vocal_separator.load_model(os.path.basename(self.config.vocal_separator_model))
        self.vocal_separator = vocal_separator

    def convert_audio(self, input_mp3_path, output_wav_path):
        if os.path.exists(output_wav_path):
            return output_wav_path
        try:
            ffmpeg.input(input_mp3_path).output(output_wav_path).run()
            logging.info(f"Conversion successful: {output_wav_path}")
        except ffmpeg.Error as e:
            logging.error(f"Error occurred during conversion: {e.stderr.decode('utf8')}")
        return output_wav_path

    def perform_vocal_separation(self):
        input_audio_path = os.path.join(self.config.input_cache, self.config.audio_file_name)
        audio_cache_path = self.audio_cache_path

        os.makedirs(audio_cache_path, exist_ok=True)

        if not input_audio_path.endswith('.wav'):
            input_audio_path = self.convert_audio(input_audio_path, input_audio_path + '.wav')

        outputs = self.vocal_separator.separate(input_audio_path)

        instrumental_audio_file = outputs[0]
        instrumental_audio_full_path = os.path.join(audio_cache_path, instrumental_audio_file)

        vocal_audio_file = outputs[-1]
        vocal_audio_full_path = os.path.join(audio_cache_path, vocal_audio_file)

        return input_audio_path, vocal_audio_full_path, instrumental_audio_full_path

class LyricsAligner:
    def __init__(self, config):
        self.config = config

    def align_lyrics(self, vocal_audio_full_path):
        input_text_path = os.path.join(self.config.input_cache, self.config.text_file_name)
        sync_file_path = os.path.join(self.config.output_cache, f"{self.config.audio_file_name}.srt")

        logging.info("Detecting lyrics language...")
        with open(input_text_path, "r", encoding="utf-8") as f:
            text = f.read()
        language, confidence = langid.classify(text)
        logging.info(f"Detected language {language} with confidence: {confidence}")

        if language != 'en':
            new_lang = "rus" if language == "ru" else ""
            if not new_lang:
                raise Exception(f"Unsupported language {language}. If you wish to use it, contact us in discord.")
            logging.info(f"Changing aligner config to {new_lang}")
            self.config.aligner_config_string = self.config.aligner_config_string.replace("eng", new_lang)
            logging.info(f"Updated aligner config {self.config.aligner_config_string}")

        logging.info('Aligning audio with lyrics...')
        task = Task(config_string=self.config.aligner_config_string)
        task.audio_file_path_absolute = vocal_audio_full_path
        task.text_file_path_absolute = input_text_path
        task.sync_map_file_path_absolute = sync_file_path

        try:
            ExecuteTask(task).execute()
            task.output_sync_map_file()
        except Exception as e:
            logging.error(f"Error during alignment: {e}")
            return None

        return sync_file_path

import os
import ffmpeg
import logging

import ffmpeg
import os
import logging

class VideoBuilder:
    def __init__(self, config):
        self.config = config
        self.default_background_path = os.path.join(self.config.input_cache, 'default.jpg')

    def get_audio_duration(self, audio_path):
        """Get the duration of the audio."""
        probe = ffmpeg.probe(audio_path)
        return float(probe['format']['duration'])

    def get_video_frame_rate(self, video_path):
        """Get the frame rate of the video."""
        try:
            probe = ffmpeg.probe(video_path)
            video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
            if video_stream:
                if 'avg_frame_rate' in video_stream:
                    num, den = map(int, video_stream['avg_frame_rate'].split('/'))
                    return num / den if den != 0 else 24
                elif 'r_frame_rate' in video_stream:
                    num, den = map(int, video_stream['r_frame_rate'].split('/'))
                    return num / den if den != 0 else 24
            return 24
        except Exception as e:
            logging.warning(f"Warning: Could not determine frame rate, using default. Error: {e}")
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

    def build_video(self, sync_file_path, input_audio_path):
        """Build the final video with the desired size and embed the original video inside it."""
        output_file_path = os.path.join(self.config.output_cache, f"{self.config.audio_file_name}_aligned.mp4")
        background_path = (
            os.path.join(self.config.input_cache, self.config.background_file_name)
            if self.config.background_file_name else self.default_background_path
        )

        frame_rate = self.get_video_frame_rate(background_path)
        duration = self.get_audio_duration(input_audio_path)

        try:
            width, height = self.config.video_resolution  # Desired final size
            aspect_ratio = self.config.aspect_ratio  # 'vertical' or 'horizontal'

            # Process background input
            is_image = background_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff'))
            if is_image:
                inv = ffmpeg.input(background_path, loop=1, t=duration, framerate=frame_rate)
            else:
                stripped_video_path = background_path + "_background_no_audio.mp4"
                background_path = self.strip_audio_from_video(background_path, stripped_video_path)
                inv = ffmpeg.input(background_path, stream_loop=-1)

            # Input audio
            ina = ffmpeg.input(input_audio_path)

            # Scale & pad video to fit inside the final resolution
            scale_filter = f"scale='if(gt(iw/ih,{width}/{height}),{width},-2)':'if(gt(iw/ih,{width}/{height}),-2,{height})'"
            pad_filter = f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black"
            vf_filters = f"{scale_filter},{pad_filter}"

            # Add subtitles and overlay text
            if sync_file_path:
                vf_filters += f",subtitles={sync_file_path}"
            if self.config.overlay_text:
                vf_filters += f",drawtext=text='{self.config.overlay_text}':x=5:y=5:fontcolor=white:fontsize='sqrt(w*h)*0.05'"

            # Combine video and audio
            out = ffmpeg.output(
                inv, ina, output_file_path,
                vf=vf_filters,
                preset="fast",
                pix_fmt="yuv420p",
                acodec="aac",
                strict="experimental",
                shortest=None,
                t=duration
            ).overwrite_output()
            out.run()
            logging.info(f"Video created successfully: {output_file_path}")
            return output_file_path
        except Exception as e:
            logging.error(f"Error occurred during video creation: {e}")
            return None


class LyricsVideoGenerator:
    def __init__(self, config):
        self.config = config
        self.audio_processor = AudioProcessor(config)
        try:
            from whisperx_aligner import LyricsAlignerWithWhisper
            self.lyrics_aligner = LyricsAlignerWithWhisper(config)
        except ImportError:
            logging.error("WhisperX is not installed. Please install it using `pip install whisperx-aligner`")
            self.lyrics_aligner = LyricsAligner(config)
            
        self.video_builder = VideoBuilder(config)

    def generate(self):
        input_audio_path, vocal_audio_full_path, instrumental_audio_full_path = self.audio_processor.perform_vocal_separation()
        if not vocal_audio_full_path:
            logging.error("Vocal separation failed.")
            return
        if self.config.production_type == "separate_audio":
            logging.info(f"Recoding audios...")
            vocal_audio_full_path = self.audio_processor.convert_audio(vocal_audio_full_path, vocal_audio_full_path+'.mp3')
            instrumental_audio_full_path = self.audio_processor.convert_audio(instrumental_audio_full_path, instrumental_audio_full_path+'.mp3')
            input_audio_path = self.audio_processor.convert_audio(input_audio_path, input_audio_path+'.mp3')
            
            result = {
                'vocal_path': vocal_audio_full_path,
                'instrumental_path': instrumental_audio_full_path,
                'audio_path': input_audio_path,
            }
            return result

        sync_file_path = self.lyrics_aligner.align_lyrics(vocal_audio_full_path)
        if not sync_file_path:
            logging.error("Lyrics alignment failed.")
            return
        is_music_production = self.config.production_type == "music"
        output_file_path = self.video_builder.build_video(sync_file_path, 
            input_audio_path=input_audio_path if is_music_production else instrumental_audio_full_path
        )
        
        result = {
                'video_path': output_file_path,
                'subtitles_path': sync_file_path
            }
        
        if result:
            logging.info(f"Result: {result}")
        else:
            logging.error("Video generation failed.")
        return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generating subtitles for music files and video with text overlay')
    parser.add_argument("--audio", help="Path to input audio", default='Nine Thou (Grant Mohrman Superstars Remix).wav', type=str)
    parser.add_argument("--text", help="Path to lyrics", default='Nine Thou (Grant Mohrman Superstars Remix).txt', type=str)
    parser.add_argument("--background", help="Path to background: video or image", default=None, type=str)
    parser.add_argument("--vocal_separator_model", help="Path to vocal separator checkpoint", default="./checkpoints/vocal_separator/Kim_Vocal_2.onnx", type=str)
    parser.add_argument("--inputs_cache", help="Path input cache folder", default='./', type=str)
    parser.add_argument("--outputs_cache", help="Path output cache folder", default='./aligner_cache/', type=str)
    args = parser.parse_args()

    config = Config(args)
    generator = LyricsVideoGenerator(config)
    generator.generate()