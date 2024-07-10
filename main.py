from fastapi import FastAPI, Request
import gemini
import asyncio
import base64
app = FastAPI()


@app.get("/")
async def confirm(request: Request):
    return "Your server is working!"
    
@app.post("/gemini/")
async def read_items(request: Request):
    
    with open("question.png", "wb") as image:
        image.write(base64.b64decode(request.query_params['image'].replace('data:image/png;base64,','')))
        
    return gemini.answer(request.query_params['key'], request.query_params['prompt'], "question.png", request.query_params['model_name'])

