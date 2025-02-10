class Config:
    def __init__(self, input_cache, output_cache, vocal_separator_model = "./checkpoints/vocal_separator/Kim_Vocal_2.onnx"):
        self.audio_file_name = None
        self.text_file_name = None
        self.background_file_name = None
        self.vocal_separator_model = vocal_separator_model
        self.input_cache = input_cache
        self.output_cache = output_cache
        self.aligner_config_string = "task_language=eng|os_task_file_format=srt|is_text_type=plain|os_task_vad_threshold=0.5|os_task_file_force_overwrite=1"
        self.overlay_text = "by Lyri.ai"
        self.production_type = 'music'
        self.gpu_on = True
        self.aspect_ratio = 'horizontal'
        self.video_resolution = (1920, 1080)
        self.use_whisper = True
        self.default_background_path = "./default.jpg"
    
    def from_user_data(self, user_data: dict):
        self.audio_file_name = user_data.get('audio_file_name')
        self.text_file_name = user_data.get('text_file_name')
        self.background_file_name = user_data.get('background_file_name')
        self.input_cache = user_data.get('input_cache', self.input_cache)
        self.output_cache = user_data.get('output_cache', self.output_cache)
        self.production_type = user_data.get('production_type', 'music')
        self.aspect_ratio = user_data.get('aspect_ratio', self.aspect_ratio)
        self.video_resolution = user_data.get('video_resolution', self.video_resolution)
        
    def from_args(self, args):
        self.audio_file_name = args.audio
        self.text_file_name = args.text
        self.background_file_name = args.background
        self.vocal_separator_model = args.vocal_separator_model
        self.input_cache = args.inputs_cache
        self.output_cache = args.outputs_cache