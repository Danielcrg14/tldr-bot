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

    # 1) Salva temporariamente o PDF
    contents = await file.read()
    tmp_path = "temp.pdf"
    with open(tmp_path, "wb") as f:
        f.write(contents)

    try:
        # 2) Extrai todo o texto
        doc = fitz.open(tmp_path)
        full_text = "".join(page.get_text() for page in doc)
        doc.close()
        os.remove(tmp_path)

        # 3) Quebra em pedaços de até 3500 chars
        max_len = 3500
        chunks = [
            full_text[i : i + max_len]
            for i in range(0, len(full_text), max_len)
        ]

        # 4) Resumir cada chunk separadamente
        mini_resumos = []
        for idx, text in enumerate(chunks, start=1):
            resp = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system",
                     "content": "Você é um assistente que resume textos em tópicos claros e objetivos."},
                    {"role": "user",
                     "content": f"***Parte {idx}***\nResuma o texto abaixo em tópicos:\n\n{text}"}
                ],
            )
            mini_resumos.append(f"**Resumo Parte {idx}:**\n{resp.choices[0].message.content}")

        # 5) Reunir todos os mini-resumos e gerar o resumo final
        todos = "\n\n".join(mini_resumos)
        final_resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system",
                 "content": "Você é um assistente que consolida resumos em um único texto coeso."},
                {"role": "user",
                 "content": "Aqui estão vários resumos de partes de um documento. Gere um resumo final em tópicos claros e objetivos:\n\n" + todos}
            ],
        )
        resumo_final = final_resp.choices[0].message.content

        return {"resumo_gerado": resumo_final}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


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
