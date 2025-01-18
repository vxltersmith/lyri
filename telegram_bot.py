import logging
import yaml
import os
import base64
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

from align_lyrics import align_lyrics
import asyncio
import tempfile
from dataclasses import dataclass
from yt_dlp import YoutubeDL
import re
import uuid


def is_youtube_url(url):
    youtube_regex = (
        r'(https?://)?(www\.|m\.)?' # Handle www. and m. subdomains
        '(youtube|youtu|youtube-nocookie|music\.youtube)\.(com|be)/' # Added music.youtube
        '(watch\?v=|embed/|v/|shorts/|playlist\?|track/|.+\?v=)?([^&=%\?]{11})' # Added track/ and playlist?
    )
    match = re.match(youtube_regex, url)
    if not match:
        return False
    # Additional validation to prevent false positives
    return len(match.group(6)) == 11

def download_youtube_video(url, output_path):
    ydl_opts = {
        'format': 'best',  # Downloads best quality video with audio
        'outtmpl': output_path,
    }
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

def file_to_base64(file_path: str) -> str:
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode()

async def handle_youtube(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger = logging.getLogger(__name__)
    message_text = update.message.text
    config = context.bot_data["config"]
    if not config.get("youtube_enabled", True):
        await update.message.reply_text("YouTube functionality is disabled.")
        return
    
    input_cache = config["paths"]["input_cache"]
    if not os.path.exists(input_cache):
        os.makedirs(input_cache, exist_ok=True)
    
    if not is_youtube_url(message_text):
        await update.message.reply_text("Not a valid YouTube URL.")
        return
    
    await update.message.reply_text("Processing YouTube video... (This might take a while)")
    
    try:
        file_name = f'{uuid.uuid4()}.mp4'
        output_path = os.path.join(input_cache, file_name)
        logger.info(f'Downloading YouTube audio to {output_path}')
        
        await asyncio.get_event_loop().run_in_executor(
            None,
            download_youtube_video,
            message_text,
            output_path
        )
        
        context.user_data['audio_file'] = {
            'file_path': output_path,
            'file_name': file_name,
            'is_youtube': True
        }
        
        await update.message.reply_text(
            "YouTube audio downloaded! Now send me the lyrics text file."
        )
            
    except Exception as e:
        logger.error(f"Error downloading YouTube video, you can try again later: {str(e)}")
        await update.message.reply_text(f"Failed to download YouTube video: {str(e)}")
        
async def save_image_file(context, image_file, input_cache, base_filename):
    image_filename = f"{base_filename}.jpg"
    image_file['file_name'] = image_filename
    image_path = os.path.join(input_cache, image_filename)
    
    file = await context.bot.get_file(image_file['file_id'])
    
    if image_file.get('is_sticker', False):
        # Download sticker and convert to JPG
        temp_path = os.path.join(input_cache, 'temp_sticker.webp')
        await file.download_to_drive(temp_path)
        
        try:
            # Import PIL with WebP support
            from PIL import Image, features
            if not features.check('webp'):
                raise ImportError("WebP support not available in PIL")
            
            with Image.open(temp_path) as img:
                # Convert to RGB mode in case it's RGBA
                if img.mode in ('RGBA', 'LA'):
                    background = Image.new('RGB', img.size, 'WHITE')
                    # Only use alpha channel if image has transparency
                    if 'A' in img.mode:
                        background.paste(img, mask=img.split()[-1])
                    else:
                        background.paste(img)
                    background.save(image_path, 'JPEG', quality=95)
                else:
                    img.convert('RGB').save(image_path, 'JPEG', quality=95)
            
        except (ImportError, OSError) as e:
            # If WebP handling fails, try using alternative converter
            try:
                from wand.image import Image as WandImage
                with WandImage(filename=temp_path) as img:
                    img.format = 'jpeg'
                    img.save(filename=image_path)
            except ImportError:
                raise Exception("Neither PIL with WebP support nor Wand is available. Please install one of them.")
        
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
    else:
        # Regular photo/document handling
        await file.download_to_drive(image_path)
    return image_path

async def align(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger = logging.getLogger(__name__)
    config = context.bot_data["config"]
    
    if not context.user_data.get('audio_file') or not context.user_data.get('lyrics_file'):
        await update.message.reply_text(
            "Please send both an audio file and a lyrics file first.\n"
            "1. Send the audio file\n"
            "2. Send the lyrics as a text file\n"
            "3. Send the image or video for background (optional) \n"
            "4. Then use /align command"
        )
        return

    await update.message.reply_text("Starting lyrics alignment process...")
    
    try:
        input_cache = config["paths"]["input_cache"]
        output_cache = config["paths"]["output_cache"]

        os.makedirs(input_cache, exist_ok=True)
        os.makedirs(output_cache, exist_ok=True)

        audio_file = context.user_data['audio_file']
        base_filename = os.path.splitext(audio_file['file_name'])[0]
        
        audio_path = os.path.join(input_cache, audio_file['file_name'])
        if audio_file.get('is_youtube'):
            audio_path = audio_file['file_path']
        else:
            file = await context.bot.get_file(audio_file['file_id'])
            await file.download_to_drive(audio_path)
        
        lyrics_file = context.user_data['lyrics_file']
        lyrics_filename = f"{base_filename}.txt"
        lyrics_file['file_name'] = lyrics_filename
        lyrics_path = await save_lyrics_file(context, lyrics_file, input_cache, base_filename)
        
        if not audio_file.get('is_youtube'):
            background_file = context.user_data.get('background_file')
            background_path = None
            if background_file:
                background_file = context.user_data['background_file']
                background_filename = f"{base_filename}.jpg"
                background_path = os.path.join(input_cache, background_filename)
                image_path = await save_image_file(context, background_file, input_cache, base_filename)
            else:
                default_bg = config["aligner"]["default_background_image"]
                if os.path.exists(default_bg):
                    background_filename = f"{base_filename}.jpg"
                    background_path = os.path.join(input_cache, background_filename)
                    import shutil
                    shutil.copy2(default_bg, background_path)
                    background_file = {}
            background_file['file_name'] = background_filename
        else:
            background_file = audio_file

        result_paths = await asyncio.get_event_loop().run_in_executor(
            None,
            align_lyrics,
            audio_file['file_name'],
            lyrics_file['file_name'],
            config["aligner"]["aligner_model_path"],
            output_cache,
            input_cache,
            background_file['file_name']
        )    
        # Send the aligned video
        video_path = result_paths['video_path']
        subtitles_path = result_paths['subtitles_path']
        audio_path = result_paths['vocal_path']
        
        # Send the aligned video
        await update.message.reply_text("Sending the aligned video...")
        with open(video_path, 'rb') as video:
            await update.message.reply_video(
                video,
                caption="Here's your video with aligned lyrics!"
            )
            
        # Send the SRT subtitles file
        await update.message.reply_text("Sending the subtitles file...")
        with open(subtitles_path, 'rb') as srt:
            await update.message.reply_document(
                srt,
                filename=f"{base_filename}.srt",
                caption="Here are the synchronized subtitles (SRT file)"
            )
            
        # Send the separated audio file
        await update.message.reply_text("Sending the audio file...")
        with open(audio_path, 'rb') as audio:
            await update.message.reply_audio(
                audio,
                filename=f"{base_filename}.mp3",
                caption="Here's the separated audio track"
            )
        # Clean up temporary files
    except Exception as e:
        logger.error(f"Error in align command: {str(e)}")
        await update.message.reply_text(f"An error occurred: {str(e)}")

    context.user_data.clear()

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    audio = update.message.audio or update.message.voice
    if audio:
        context.user_data['audio_file'] = {
            'file_id': audio.file_id,
            'file_name': getattr(audio, 'file_name', 'audio.wav')
        }
        await update.message.reply_text("Audio file received! Now send me the lyrics text file.")

def load_settings(config_path="./configs/bot.yaml"):
    with open(config_path, "r") as file:
        settings = yaml.safe_load(file)
    return settings

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.document:
        # Handle document upload
        document = update.message.document
        if document and document.file_name.endswith('.txt'):
            context.user_data['lyrics_file'] = {
                'file_id': document.file_id,
                'file_name': document.file_name,
                'is_text_message': False
            }
            await update.message.reply_text("Lyrics file received! Use /align to start the alignment process.")
    else:
        # Handle plain text message
        text = update.message.text
        context.user_data['lyrics_file'] = {
            'text_content': text,
            'file_name': 'lyrics.txt',
            'is_text_message': True
        }
        await update.message.reply_text("Lyrics text received! Use /align to start the alignment process.")

# Update the file handling logic
async def save_lyrics_file(context, lyrics_file, input_cache, base_filename):
    lyrics_filename = f"{base_filename}.txt"
    lyrics_file['file_name'] = lyrics_filename
    lyrics_path = os.path.join(input_cache, lyrics_filename)
    
    if lyrics_file.get('is_text_message', False):
        # Save text message content to file
        with open(lyrics_path, 'w', encoding='utf-8') as f:
            f.write(lyrics_file['text_content'])
    else:
        # Download and save document
        file = await context.bot.get_file(lyrics_file['file_id'])
        await file.download_to_drive(lyrics_path)
    
    return lyrics_path

async def handle_background_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.sticker:
        # Handle sticker
        sticker = update.message.sticker
        context.user_data['background_file'] = {
            'file_id': sticker.file_id,
            'file_name': 'cover.webp',  # Stickers are typically in WebP format
            'is_sticker': True
        }
        await update.message.reply_text("Cover image (sticker) received! Use /align when you're ready.")
    else:
        photo = update.message.photo[-1] if update.message.photo else None
        if photo:
            context.user_data['background_file'] = {
                'file_id': photo.file_id,
                'file_name': 'background.jpg'
            }
            await update.message.reply_text("Background image received! You can now use /align to start the alignment process.")

def load_settings(config_path="./configs/bot.yaml"):
    with open(config_path, "r") as file:
        settings = yaml.safe_load(file)
    return settings

def setup_logging(log_config):
    log_level = log_config.get("level", "INFO").upper()
    log_file = log_config.get("file", "./logs/bot.log")
    
    if not os.path.exists(os.path.dirname(log_file)):
        os.makedirs(os.path.dirname(log_file))

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    welcome_message = context.bot_data.get("welcome_message", "Welcome to the bot!")
    await update.message.reply_text(welcome_message)
    logger = logging.getLogger(__name__)
    logger.info(f"User {update.message.from_user.id} started the bot.")

def main():
    config_path = "./configs/bot.yaml"
    if not os.path.exists(config_path):
        print(f"Configuration file not found: {config_path}")
        return

    settings = load_settings(config_path)
    bot_token = str(settings["bot"]["token"])
    settings["bot"]["token"] = ""
    welcome_message = settings["bot"]["welcome_message"]
    
    setup_logging(settings["log"])

    app = ApplicationBuilder().token(bot_token).build()

    app.bot_data["welcome_message"] = welcome_message
    app.bot_data["config"] = settings

    app.add_handler(CommandHandler("align", lambda update, context: align(update, context)))
    app.add_handler(CommandHandler("start", lambda update, context: start(update, context)))
    app.add_handler(MessageHandler(filters.AUDIO | filters.VOICE, handle_audio))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE | filters.Sticker.ALL, handle_background_image))
    # YouTube handler should come before the general text handler
    app.add_handler(MessageHandler(
        filters.TEXT & (
            filters.Regex(r'.*youtube\.com.*') |
            filters.Regex(r'.*youtu\.be.*') |
            filters.Regex(r'.*music\.youtube\.com.*')
        ),
        handle_youtube
    ))
    # Handle text files and plain text (excluding YouTube URLs)
    app.add_handler(MessageHandler(
        (filters.Document.TEXT | filters.TEXT), 
        handle_document
    ))

    logger = logging.getLogger(__name__)
    logger.info("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()