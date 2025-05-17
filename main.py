from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import fitz  # PyMuPDF
import os
from dotenv import load_dotenv
from openai import OpenAI

# Carrega sua chave do OpenAI do arquivo .env na raiz
load_dotenv()
client = OpenAI()

# Cria a aplicação FastAPI
app = FastAPI()

# Monta a pasta 'static' na raiz para servir o index.html
app.mount("/", StaticFiles(directory="static", html=True), name="static")

# Rota de health-check
@app.get("/ping")
def ping():
    return {"ok": True}

# Rota de upload de PDF que gera o resumo com GPT-4o
@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    # Valida extensão
    if not file.filename.lower().endswith(".pdf"):
        return JSONResponse(status_code=400, content={"error": "Envie um PDF válido."})

    # Salva temporariamente
    contents = await file.read()
    tmp_path = "temp.pdf"
    with open(tmp_path, "wb") as f:
        f.write(contents)

    try:
        # Extrai texto do PDF
        doc = fitz.open(tmp_path)
        full_text = "".join(page.get_text() for page in doc)
        doc.close()
        os.remove(tmp_path)

        # Limita para evitar excesso de tokens
        trimmed_text = full_text[:4000]

        # Chama o GPT-4o para resumir
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Você é um assistente que resume textos com clareza e objetividade em tópicos."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Resuma o conteúdo abaixo em tópicos claros e objetivos:\n\n"
                        f"{trimmed_text}"
                    ),
                },
            ],
        )

        resumo = response.choices[0].message.content
        return {"resumo_gerado": resumo}

    except Exception as e:
        # Retorna erro 500 em caso de falha
        return JSONResponse(status_code=500, content={"error": str(e)})
