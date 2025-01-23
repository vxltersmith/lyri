import logging
import yaml
import os
import base64
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram import Bot

from align_lyrics import Config, LyricsVideoGenerator
import asyncio
import tempfile
from dataclasses import dataclass
from yt_dlp import YoutubeDL
import re
import uuid


import os
import aiohttp
import aiofiles

import subprocess
import time

def start_local_server(api_id, api_hash):
    try:
        # Start the local server
        subprocess.Popen([
            "./telegram-bot-api/build/telegram-bot-api",
            "--local",
            f"--api-id={api_id}",
            f"--api-hash={api_hash}"
        ])
        # Wait for the server to start
        time.sleep(5)  # Adjust the sleep time as needed
        print("Local server started successfully.")
    except Exception as e:
        print(f"Failed to start local server: {e}")


async def download_file_in_chunks(context, file_id, file_path, chunk_size=1024 * 1024):
    file = await context.bot.get_file(file_id)
    file_url = file.file_path
    
    try:
        await file.download_to_drive(file_path)
    except Exception as e:
        print("Failed to download file with main API, fall back on web download")
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as response:
                async with aiofiles.open(file_path, 'wb') as f:
                    while True:
                        chunk = await response.content.read(chunk_size)
                        if not chunk:
                            break
                        await f.write(chunk)
    except Exception as e:
        print(f"Failed to download file: {e}")

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
        await try_start_processing(update, context)
            
    except Exception as e:
        logger.error(f"Error downloading YouTube video, you can try again later: {str(e)}")
        
        inline_keyboard = [
            [InlineKeyboardButton("Retry download video", callback_data='yt_retry')],
            [InlineKeyboardButton("Drop current context / Начать сначала", callback_data='drop_context')]
        ]
    
        markup = InlineKeyboardMarkup(inline_keyboard)
        
        await update.message.reply_text(f"Failed to download YouTube video: {str(e)}", reply_markup=markup)
        
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

async def align(update: Update, context: ContextTypes.DEFAULT_TYPE, production_type: str) -> None:
    logger = logging.getLogger(__name__)
    config = context.bot_data["config"]
    
    track_recieved = context.user_data.get('audio_file') or  context.user_data.get('video_file')
    
    if not track_recieved or not context.user_data.get('lyrics_file'):
        await update.message.reply_text(
            "Please send both an audio file and a lyrics file first.\n"
            "1. Send the audio file\n"
            "2. Send the lyrics as a text file\n"
            "3. Send the image or video for background (optional) \n"
            "4. Then use buttons to start alignment process"
        )
        return

    await update.effective_chat.send_message("Starting lyrics alignment process...")
    
    try:
        input_cache = config["paths"]["input_cache"]
        output_cache = config["paths"]["output_cache"]

        os.makedirs(input_cache, exist_ok=True)
        os.makedirs(output_cache, exist_ok=True)

        audio_file = context.user_data.get('audio_file')
        video_file = context.user_data.get('video_file')
        base_filename = None

        if audio_file:
            base_filename = os.path.splitext(audio_file['file_name'])[0]
            audio_path = os.path.join(input_cache, audio_file['file_name'])
            if audio_file.get('is_youtube'):
                audio_path = audio_file['file_path']
            else:
                file = await context.bot.get_file(audio_file['file_id'])
                await file.download_to_drive(audio_path)
            source_file = audio_file
        elif video_file:
            base_filename = os.path.splitext(video_file['file_name'])[0]
            video_path = os.path.join(input_cache, video_file['file_name'])
            try:
                await download_file_in_chunks(context, video_file['file_id'], video_path)
            except:
                await update.effective_chat.send_message(f"An error occurred: {str(e)} \n Currently Telegram does not support downloading files larger than 20Mb in bot API. Please try with a smaller file.")
            source_file = video_file
                
        lyrics_file = context.user_data['lyrics_file']
        lyrics_filename = f"{base_filename}.txt"
        lyrics_file['file_name'] = lyrics_filename
        lyrics_path = await save_lyrics_file(context, lyrics_file, input_cache, base_filename)
        
        background_file = context.user_data.get('background_file')
        background_path = None
        if background_file and not background_file.get('is_video_file'):
            background_file = context.user_data['background_file']
            background_filename = f"{base_filename}.jpg"
            background_path = os.path.join(input_cache, background_filename)
            await save_image_file(context, background_file, input_cache, base_filename)
            background_file['file_name'] = background_filename
        elif background_file and background_file.get('is_video_file'):
            video_path = os.path.join(input_cache, background_file['file_name'])
            try:
                await download_file_in_chunks(context, background_file['file_id'], video_path)
            except:
                await update.effective_chat.send_message(f"An error occurred: {str(e)} \n Currently Telegram does not support downloading files larger than 20Mb in bot API. Please try with a smaller file.")
        else:
            if source_file.get('is_youtube') or source_file.get("is_video_file"):
                background_file = source_file
            else:    
                default_bg = config["aligner"]["default_background_image"]
                if os.path.exists(default_bg):
                    background_filename = f"{base_filename}.jpg"
                    background_path = os.path.join(input_cache, background_filename)
                    import shutil
                    shutil.copy2(default_bg, background_path)
                    background_file = {}
                background_file['file_name'] = background_filename
                
        config = context.bot_data['aligner_config']
        generator = context.bot_data['aligner_generator']
        
        data = {
            'audio_file_name': source_file['file_name'],
            'text_file_name': lyrics_file['file_name'],
            'background_file_name': background_file['file_name'],
            'input_cache': input_cache,
            'output_cache': output_cache,
            'production_type': production_type   
        }
        config.from_user_data(data)

        result_paths = await asyncio.get_event_loop().run_in_executor(
            None,
           generator.generate
        )
        
        # Send the aligned video
        video_path = result_paths['video_path']
        subtitles_path = result_paths['subtitles_path']
        vocal_audio_full_path = result_paths['vocal_path']
        instrumental_audio_full_path = result_paths['instrumental_path']
        input_audio_path = result_paths['audio_path']
        
        # Send the aligned video
        await update.effective_chat.send_message("Sending the aligned video...")
        with open(video_path, 'rb') as video:
            await update.effective_chat.send_video(
                video,
                caption="Here's your video with aligned lyrics!"
            )
            
        # Send the SRT subtitles file
        await update.effective_chat.send_message("Sending the subtitles file...")
        with open(subtitles_path, 'rb') as srt:
            await update.effective_chat.send_document(
                srt,
                filename=f"{base_filename}.srt",
                caption="Here are the synchronized subtitles (SRT file)"
            )
            
        # Send the separated audio file
        await update.effective_chat.send_message("Sending vocal audio file...")
        with open(vocal_audio_full_path, 'rb') as audio:
            await update.effective_chat.send_audio(
                audio,
                filename=f"{base_filename}.mp3",
                caption="Here's the vocal audio track"
            )
        
        # Send the instrumental audio file
        await update.effective_chat.send_message("Sending instrumental audio file...")
        with open(instrumental_audio_full_path, 'rb') as audio:
            await update.effective_chat.send_audio(
                audio,
                filename=f"{base_filename}_instrumental.mp3",
                caption="Here's the instrumental audio track"
            )
            
        if source_file.get('is_youtube') or video_file:    
            # Send the original audio file
            await update.effective_chat.send_message("Sending original audio file...")
            with open(input_audio_path, 'rb') as audio:
                await update.effective_chat.send_audio(
                    audio,
                    filename=f"{base_filename}.mp3",
                    caption="Here's the original audio track"
                )
            
        # Clean up temporary files
        context.user_data.clear()
    except Exception as e:
        logger.error(f"Error in align command: {str(e)}")
        await update.effective_chat.send_message(f"An error occurred: {str(e)}")
        await try_start_processing(update, context)
    
    
def is_context_full(user_data: dict) -> bool:
    # Ensure either video_file or audio_file is present, but not both, and lyrics_text is provided
    has_video = 'video_file' in user_data
    has_audio = 'audio_file' in user_data
    has_lyrics = 'lyrics_file' in user_data
    return has_lyrics and (has_video != has_audio)  # XOR: one of video or audio, not both

async def try_start_processing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_data = context.user_data

    if not is_context_full(user_data):
        # Identify missing keys
        has_video = 'video_file' in user_data
        has_audio = 'audio_file' in user_data
        has_lyrics = 'lyrics_file' in user_data

        # Construct the missing parts message
        if not has_lyrics:
            missing_parts = "the lyrics"
        elif not has_video and not has_audio:
            missing_parts = "either a video or an audio file"
        elif has_video and has_audio:
            missing_parts = "only one of a video file or an audio file (not both)"

        output_message = (
            f"To proceed, I need {missing_parts}. "
            "If you're unsure, feel free to ask for help! 😊"
        )
        
        # Add inline button for dropping the context
        inline_keyboard = [
            [InlineKeyboardButton("Drop current context / Начать сначала", callback_data='drop_context')]
        ]
        
        if not has_lyrics and (has_audio and not user_data['audio_file'].get("is_youtube", False) and user_data['audio_file']['title'] and user_data['audio_file']['performer']):
            inline_keyboard.append(
                [InlineKeyboardButton("Search for lyrics / Найти текст online (expirimental)", callback_data='search_lyrics')]
            )
    
        markup = InlineKeyboardMarkup(inline_keyboard)

        await update.message.reply_text(output_message, reply_markup=markup)
        return

    bot_config = context.bot_data['config']
    config = Config(input_cache=bot_config['paths']['input_cache'], 
        output_cache=bot_config['paths']['output_cache'], 
        vocal_separator_model=bot_config["aligner"]["aligner_model_path"],)
    generator = LyricsVideoGenerator(config)
    context.bot_data['aligner_config'] = config
    context.bot_data['aligner_generator'] = generator

    # If context is valid
    ready_text = "Great! Everything is ready. What would you like to create? 🎬 \n"
    if 'background_file' not in user_data:
        ready_text += "(Or you can send me an image for background)"
    await update.effective_chat.send_message(ready_text)
    inline_keyboard = [
        [InlineKeyboardButton("Music video", callback_data='music_align')],
        [InlineKeyboardButton("Karaoke video", callback_data='karaoke_align')]
    ]
    markup = InlineKeyboardMarkup(inline_keyboard)
    await update.effective_chat.send_message("Choose an option below to get started:", reply_markup=markup)


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    audio = update.message.audio or update.message.voice
    if audio:
        orignal_file_name = getattr(audio, 'file_name', 'audio.wav')
        extension = os.path.splitext(orignal_file_name)[-1]
        file_name = f'audio_{uuid.uuid4()}{extension}'
        context.user_data['audio_file'] = {
            'file_id': audio.file_id,
            'file_name': file_name,
            'is_audio_file': True,
            'title': audio.title if hasattr(audio, 'title') else None,
            'performer': audio.performer if hasattr(audio, 'performer') else None
        }
        await update.message.reply_text("Audio file received! Keep going!")
        await try_start_processing(update, context)
        
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    video = update.message.video
    if video:
        key = 'background_file' if context.user_data.get('audio_file') else 'video_file'
        context.user_data[key] = {
            'file_id': video.file_id,
            'file_name': f'video_{uuid.uuid4()}.mp4',
            'is_video_file': True
        }
        await update.message.reply_text("Video file received!")
        await try_start_processing(update, context)

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
        await update.message.reply_text("Lyrics text received!")
        await try_start_processing(update, context)

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
        await update.message.reply_text("Cover image (sticker) received!")
    else:
        photo = update.message.photo[-1] if update.message.photo else None
        if photo:
            context.user_data['background_file'] = {
                'file_id': photo.file_id,
                'file_name': 'background.jpg'
            }
            await update.message.reply_text("Background image received!")
    await try_start_processing(update, context)

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()  # Acknowledge the button click

    # Handle each callback data case
    if query.data == 'music_align':
        await query.edit_message_text("You selected: Music video 🎥. Processing will begin soon!")
        await align(update, context, 'music')
    elif query.data == 'karaoke_align':
        await query.edit_message_text("You selected: Karaoke video 🎤. Processing will begin soon!")
        await align(update, context, 'karaoke')
    elif query.data == 'cancel':
        await query.edit_message_text("Processing cancelled. You can start a new session now. 😊")
    elif query.data == 'drop_context':
        context.user_data.clear()  # Clear user data
        await query.edit_message_text("Context cleared. You can start fresh now. 😊")
    elif query.data == 'yt_retry':
        await query.edit_message_text("Retrying YouTube download. Please wait...")
        await download_youtube_video(update, context, context.user_data['yt_url'])
    else:
        await query.edit_message_text("Unknown option. Please try again.")


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

import argparse
def main():
    parser = argparse.ArgumentParser(description="Telegram Bot")
    parser.add_argument("--config", type=str, default="./configs/default.yaml", help="Path to the configuration file")
    args = parser.parse_args()
    config_path = args.config
    if not os.path.exists(config_path):
        print(f"Configuration file not found: {config_path}")
        return
    settings = load_settings(config_path)
    
    setup_logging(settings["log"])

    app_id = settings["bot"].get("APP_ID")
    app_hash = settings["bot"].get("API_HASH")
    bot_token = str(settings["bot"]["token"])
    bot = None
    if app_id and app_hash:
        # Start the local server
        start_local_server(app_id, app_hash)
        # Configure the bot to use the local server
        session = AiohttpSession(api=TelegramAPIServer.from_base("http://localhost:8081", is_local=True))
        bot = Bot(token=bot_token, session=session)
    
    app = ApplicationBuilder()
    if bot:
        app = app.bot(bot).build()
    else:
        app = app.token(bot_token).build()

    app.bot_data["welcome_message"] = settings["bot"]["welcome_message"]
    app.bot_data["config"] = settings

    app.add_handler(CallbackQueryHandler(handle_callback_query))
    app.add_handler(CommandHandler("start", lambda update, context: start(update, context)))
    app.add_handler(MessageHandler(filters.AUDIO | filters.VOICE, handle_audio))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
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