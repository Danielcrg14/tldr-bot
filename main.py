from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import fitz
import os
from dotenv import load_dotenv
from openai import OpenAI

# Carrega variáveis de .env
load_dotenv()
client = OpenAI()

app = FastAPI()

# 1) Serve os arquivos estáticos (JS/CSS/HTML secundarios) em /static
app.mount("/static", StaticFiles(directory="static"), name="static")

# 2) Rota raiz: devolve o index.html
@app.get("/", include_in_schema=False)
async def serve_index():
    return FileResponse("static/index.html")

# 3) Health check
@app.get("/ping")
def ping():
    return {"ok": True}

# 4) Upload de PDF → resumo
@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        return JSONResponse(status_code=400, content={"error": "Envie um PDF válido."})

    contents = await file.read()
    tmp_path = "temp.pdf"
    with open(tmp_path, "wb") as f:
        f.write(contents)

    try:
        doc = fitz.open(tmp_path)
        full_text = "".join(page.get_text() for page in doc)
        doc.close()
        os.remove(tmp_path)

        trimmed = full_text[:4000]

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "Você é um assistente que resume textos em tópicos claros e objetivos."
                },
                {
                    "role": "user",
                    "content": f"Resuma em tópicos:\n\n{trimmed}"
                }
            ]
        )
        resumo = response.choices[0].message.content
        return {"resumo_gerado": resumo}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
