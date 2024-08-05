from fastapi import FastAPI, Request
import asyncio
import base64
import telegram
import time
import threading

start = time.time()
async def func():
    bot = telegram.Bot("7296494753:AAFHYL8LtoGNHyWZs3yiyQV0S3gYrR5YhHA")
    async with bot:
        while True:
            time.sleep(60)
            await bot.sendMessage(chat_id='@thek1ll3r', text=f'{round(time.time()-start)/60} minutes have passed since i have been alive')

def main():
    asyncio.run(func())

thread = threading.Thread(target=main,)
thread.start()
app = FastAPI()


@app.get("/")
async def confirm(request: Request):
    return "Your server is working!"
