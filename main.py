from fastapi import FastAPI, Request
import asyncio
import telegram
import time
import os
import threading

start = time.time()
async def func():
    bot = telegram.Bot(os.environ['APIKEY'])
    the_killers_monologue = "i am what i am./ i serve no god, or country./ i fly no flag./ if i'm effective, it's because of one simple fact./ i./ don't/ give./ a./ fuck."
    for i in the_killers_monologue.split('/'):
        await bot.sendMessage(chat_id='@th3k1ll3r', text="i)
        time.sleep(2)
    async with bot:
        while True:
            await bot.sendMessage(chat_id='@th3k1ll3r', text=f'~{round((time.time()-start)/60)} minutes have passed since i have been alive')
            time.sleep(60)

def main():
    asyncio.run(func())

thread = threading.Thread(target=main,)
thread.start()
app = FastAPI()


@app.get("/")
async def confirm(request: Request):
    return "Your server is working!"
