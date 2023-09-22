import os
import random
import traceback

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

import vk_api
from telegram import Bot
from deta import Deta
import requests
import asyncio
import time
import io
from PIL import Image
from dotenv import load_dotenv
load_dotenv()

# Deta credentials
DETA_PROJECT_KEY = ''  # Replace with your Deta project key
DETA_DRIVE_NAME = ''  # Replace with your Deta Drive name

# Initialize Deta
deta = Deta(DETA_PROJECT_KEY)
drive = deta.Drive(DETA_DRIVE_NAME)


# VK.com credentials
VK_ACCESS_TOKEN = ''  # Replace with your VK access token
VK_OWNER_ID = '' #With "-"

# Telegram credentials
TELEGRAM_TOKEN = ''  # Replace with your Telegram Bot API token
TELEGRAM_CHANNEL_ID = ''  # Replace with your Telegram channel ID
TELEGRAM_CHANNEL_NAME = ''
TELEGRAM_USER_ID = ''

gif_name = "gif"

def log(message):
    timestamp = time.strftime("%H:%M:%S :", time.localtime())
    asyncio.run(send_message_to_telegram(f"{timestamp}"+message))
    print(f"{timestamp}"+message)

def sleep_random_time(min_time = 1, max_time = 1):
    sleep_duration = random.uniform(min_time * 60, max_time * 60)
    log("Sleep for: "+str(sleep_duration)+" seconds.")
    time.sleep(sleep_duration)
    log("Sleep for: "+str(sleep_duration) + "seconds is over")



async def send_message_to_telegram(message):
    bot = Bot(token=TELEGRAM_TOKEN)
    await bot.send_message(chat_id=TELEGRAM_USER_ID, text=message)

async def post_image_to_telegram(file_content, caption = None):
    bot = Bot(token=TELEGRAM_TOKEN)

    message = await bot.send_photo(chat_id=TELEGRAM_CHANNEL_ID, photo=file_content, caption=caption)

    telegram_post_link = f"https://t.me/{TELEGRAM_CHANNEL_NAME}/{(message.message_id)}"

    print("Image posted to Telegram channel successfully!")

    return telegram_post_link

def post_image_to_vk(file_content, telegram_post_link, message = None):
    vk_session = vk_api.VkApi(token=VK_ACCESS_TOKEN)
    vk = vk_session.get_api()

    # Upload the image
    upload_url = vk.photos.getWallUploadServer()['upload_url']

    #Converting downloaded image from bytes object to BufferedReader
    image = Image.open(io.BytesIO(file_content))
    output_buffer = io.BytesIO()
    output_buffer.name = "temp.png"
    image.save(output_buffer, format='PNG')

    output_buffer.seek(0)
    buffered_reader = io.BufferedReader(output_buffer)

    response = vk_session.http.post(upload_url, files={'photo': buffered_reader})
    photo_data = response.json()

    # Save uploaded photo
    saved_photo = vk.photos.saveWallPhoto(server=photo_data['server'],
                                          photo=photo_data['photo'],
                                          hash=photo_data['hash'])[0]

    # Post the image to VK.com
    vk.wall.post(owner_id=VK_OWNER_ID,  # Replace with the owner ID (user or community)
                 from_group=1,  # Set to 1 if posting as a community, 0 if posting as a user
                 copyright=telegram_post_link,
                 message= message,
                 attachments=f"photo{saved_photo['owner_id']}_{saved_photo['id']}")

    print("Image posted to VK.com successfully!")

async def post_gif_to_telegram(file_content, caption=None):
    bot = Bot(token=TELEGRAM_TOKEN)

    # Converting the downloaded GIF from bytes object to BufferedReader
    buffered_reader = io.BytesIO(file_content)
    buffered_reader.name = f"{gif_name}.gif"

    message = await bot.send_animation(chat_id=TELEGRAM_CHANNEL_ID, animation=buffered_reader, caption=caption)

    telegram_post_link = f"https://t.me/{TELEGRAM_CHANNEL_NAME}/{message.message_id}"

    print("GIF posted to Telegram channel successfully!")

    return telegram_post_link

def post_gif_to_vk(file_content, telegram_post_link, message = None):
    try:
        vk_session = vk_api.VkApi(token=VK_ACCESS_TOKEN)
        vk = vk_session.get_api()
        asyncio.run(send_message_to_telegram(str(time.strftime("%H:%M:%S : Started posting gif to vk", time.localtime()))))
        # Upload the GIF
        upload_url = vk.docs.getMessagesUploadServer(type='doc', peer_id=VK_OWNER_ID)['upload_url']
        # Converting the downloaded GIF from bytes object to BufferedReader
        buffered_reader = io.BytesIO(file_content)
        buffered_reader.name = f"{gif_name}.gif"
        response = requests.post(upload_url, files={'file': buffered_reader})
        upload_data = response.json()
        # Save uploaded document
        saved_doc = vk.docs.save(file=upload_data['file'], title='GIF')

        sds = f"doc{saved_doc['doc']['owner_id']}_{saved_doc['doc']['id']}"
        # Post the GIF to VK.com
        vk.wall.post(owner_id=VK_OWNER_ID,  # Replace with the owner ID (user or community)
                     from_group=1,  # Set to 1 if posting as a community, 0 if posting as a user
                     copyright=telegram_post_link,
                     message=message,
                     attachments=f"doc{saved_doc['doc']['owner_id']}_{saved_doc['doc']['id']}")

        print("GIF posted to VK.com successfully!")
        asyncio.run(send_message_to_telegram(
            str(time.strftime("%H:%M:%S : Finished posting to vk. ", time.localtime()))))
    except Exception as e:
        log(''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__)))

app = FastAPI()

class NestedEventModel(BaseModel):
    id: str
    trigger: str

class Event(BaseModel):
    event: NestedEventModel


@app.get("/")
def root():
    return "hi!"


@app.post('/__space/v0/actions')
def actions(event: Event):
    try:
        log("Event triggered")
        #sleep_random_time(int(os.getenv("MIN_SLEEP_TIME")), int(os.getenv("MAX_SLEEP_TIME")))

        text_file_content = None
        files = drive.list()
        if files['names']:
            for file_name in files['names']:
                file_extension = os.path.splitext(file_name)[1].lower()
                if file_extension in ['.jpg', '.jpeg', '.png', '.gif']:
                    log("Found image file: " + str(file_name))
                    picture_file = drive.get(file_name).read()

                    ff_name = files['names'][0]
                    print("Started posting file " + str(ff_name))

                    text_file_name=os.path.splitext(file_name)[0] + '.txt'
                    if text_file_name in files['names']:
                        log("Found corresponding text file: " + str(text_file_name))
                        text_file_content = (drive.get(text_file_name).read()).decode("utf-8")
                        log("posting a file: " + str(file_name) + " files left before the post: " + str(len(files['names'])))

                    if file_extension == ".gif":
                        log("Posting gif file: " + str(file_name))
                        telegram_post_link = asyncio.run(post_gif_to_telegram(picture_file, text_file_content))
                        post_gif_to_vk(picture_file, telegram_post_link, text_file_content)

                        drive.delete(file_name)
                        log(f"File {file_name} deleted successfully!")
                    else:
                        log("Posting static image file: " + str(file_name))
                        telegram_post_link = asyncio.run(post_image_to_telegram(picture_file, text_file_content))
                        post_image_to_vk(picture_file, telegram_post_link, text_file_content)

                        drive.delete(file_name)
                        log(f"File {file_name} deleted from Deta Drive successfully!")
                        # if text_file_name in files['names']:
                        #     drive.delete(text_file_name)
                        #     log("Text file deleted from Deta Drive successfully!")

                        if text_file_content is None:
                            log("No corresponding text file found for file: " + str(text_file_name))

                    break  # Exit the loop after processing the first image file
                else:
                    log("Image file not found")
        else:
            log("No files found.")

    except Exception as e:
        log(''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__)))

