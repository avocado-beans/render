from fastapi import FastAPI, Request
import gemini
import asyncio
import base64
app = FastAPI()


@app.get("/")
async def confirm(request: Request):
    return "Your server is working!"
    
@app.post("/image/")
async def read_image(request: Request):
    
    with open("question.png", "wb") as image:
        image.write(base64.b64decode(request.query_params['image'].replace('data:image/png;base64,','')))
        
    return gemini.text_in_image(request.query_params['key'], request.query_params['prompt'], "question.png", request.query_params['model_name'])

@app.post("/text/")
async def read_text(request: Request):
    
    return gemini.text_only(request.query_params['key'], request.query_params['prompt'], request.query_params['model_name'])


