
import logging
from aligners import LyricsAlignerWithWhisper, LyricsAligner
import argparse
from config import Config


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


from video_builder import VideoBuilder
from audio_processor import AudioProcessor

class LyricsVideoGenerator:
    def __init__(self, config):
        self.config = config
        self.audio_processor = AudioProcessor(config)
        if config.use_whisper:
            self.lyrics_aligner = LyricsAlignerWithWhisper(config)
        else:
            self.lyrics_aligner = LyricsAligner(config)            
        self.video_builder = VideoBuilder(config)

    def generate(self, task_config: Config):
        input_audio_path, vocal_audio_full_path, instrumental_audio_full_path = self.audio_processor.perform_vocal_separation(task_config)
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

        sync_file_path = self.lyrics_aligner.align_lyrics(vocal_audio_full_path, task_config)
        if not sync_file_path:
            logging.error("Lyrics alignment failed.")
            return
        is_music_production = self.config.production_type == "music"
        output_file_path = self.video_builder.build_video(sync_file_path, 
            input_audio_path=input_audio_path if is_music_production else instrumental_audio_full_path,
            task_config = task_config
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