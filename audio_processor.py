import os
import ffmpeg
from config import Config
from audio_separator.separator import Separator
import logging


class AudioProcessor:
    def __init__(self, config):
        self.config = config
        self.audio_cache_path = os.path.join(self.config.input_cache, "audio_cache")
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
            logging.error(
                f"Error occurred during conversion: {e.stderr.decode('utf8')}"
            )
        return output_wav_path

    def perform_vocal_separation(self, task_config: Config):
        input_audio_path = os.path.join(
            self.config.input_cache, task_config.audio_file_name
        )
        audio_cache_path = self.audio_cache_path

        os.makedirs(audio_cache_path, exist_ok=True)

        if not input_audio_path.endswith(".wav"):
            input_audio_path = self.convert_audio(
                input_audio_path, input_audio_path + ".wav"
            )

        outputs = self.vocal_separator.separate(input_audio_path)

        instrumental_audio_file = outputs[0]
        instrumental_audio_full_path = os.path.join(
            audio_cache_path, instrumental_audio_file
        )

        vocal_audio_file = outputs[-1]
        vocal_audio_full_path = os.path.join(audio_cache_path, vocal_audio_file)

        return input_audio_path, vocal_audio_full_path, instrumental_audio_full_path
