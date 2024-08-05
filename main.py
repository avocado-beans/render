from fastapi import FastAPI, Request
import asyncio
import telegram
import time
import os
import threading

start = time.time()
async def func():
    bot = telegram.Bot(os.environ['APIKEY'])
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
