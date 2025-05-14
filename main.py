from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
import fitz  # PyMuPDF
import os
from dotenv import load_dotenv
from openai import OpenAI

# ──────────────────────────────────────────────────────────
# 1) Carrega a chave armazenada no arquivo .env
#    (.env deve conter OPENAI_API_KEY=sk-…)
# ──────────────────────────────────────────────────────────
load_dotenv()
client = OpenAI()  # já usa a OPENAI_API_KEY do ambiente

app = FastAPI()


@app.get("/ping")
def ping():
    """Health-check simples."""
    return {"ok": True}


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Recebe um PDF, extrai o texto e devolve um resumo gerado pelo GPT-4o
    em tópicos claros e objetivos.
    """
    # 1) Validação rápida
    if not file.filename.lower().endswith(".pdf"):
        return JSONResponse(
            status_code=400,
            content={"error": "Envie um arquivo PDF válido."},
        )

    # 2) Salva o PDF temporariamente
    contents = await file.read()
    tmp_path = "temp.pdf"
    with open(tmp_path, "wb") as f:
        f.write(contents)

    try:
        # 3) Extrai texto com PyMuPDF
        doc = fitz.open(tmp_path)
        full_text = "".join(page.get_text() for page in doc)
        doc.close()
        os.remove(tmp_path)

        # 4) Limita tamanho para evitar excesso de tokens
        trimmed_text = full_text[:4000]

        # 5) Chama o GPT-4o para resumir
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Você é um assistente que resume textos com clareza, "
                        "objetividade e em tópicos."
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
        # Caso ocorra qualquer erro, devolve 500 com detalhe
        return JSONResponse(status_code=500, content={"error": str(e)})
