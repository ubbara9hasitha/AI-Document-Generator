import json
import os
import re
from datetime import datetime
from pathlib import Path
from io import BytesIO

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from docx import Document
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = BASE_DIR / "knowledge"
DATA_DIR = BASE_DIR / "data"
HISTORY_FILE = DATA_DIR / "history.json"
KNOWLEDGE_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

app = FastAPI(title="DocuAI API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN, "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class GenerateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    document_type: str = "Project Report"
    requirements: str = Field(min_length=3)
    extra_context: str = ""

class ExportRequest(BaseModel):
    title: str
    content: str

def retrieve_context(query: str, top_k: int = 3) -> str:
    """Retrieve relevant paragraphs from .txt files using TF-IDF similarity."""
    documents = []
    for path in KNOWLEDGE_DIR.glob("*.txt"):
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError:
            continue
        chunks = [p.strip() for p in re.split(r"\n\s*\n", raw) if p.strip()]
        documents.extend((path.name, chunk) for chunk in chunks)

    if not documents:
        return ""

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        corpus = [chunk for _, chunk in documents]
        vectorizer = TfidfVectorizer(stop_words="english")
        matrix = vectorizer.fit_transform(corpus + [query])
        scores = cosine_similarity(matrix[-1], matrix[:-1]).ravel()
        best = scores.argsort()[::-1][:top_k]
        selected = [
            f"[Source: {documents[i][0]}]\n{documents[i][1]}"
            for i in best if scores[i] > 0
        ]
        return "\n\n".join(selected)
    except ValueError:
        return ""

def save_history(item: dict):
    history = []
    if HISTORY_FILE.exists():
        try:
            history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            history = []
    history.insert(0, item)
    HISTORY_FILE.write_text(json.dumps(history[:50], indent=2), encoding="utf-8")

@app.get("/")
def home():
    return {"message": "DocuAI API is running"}

@app.get("/api/health")
def health():
    return {"status": "ok", "model": OLLAMA_MODEL}

@app.get("/api/history")
def get_history():
    if not HISTORY_FILE.exists():
        return []
    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

@app.post("/api/generate")
def generate_document(payload: GenerateRequest):
    context = retrieve_context(payload.requirements + " " + payload.extra_context)
    prompt = f"""
You are DocuAI, an assistant that creates clear, accurate, well-structured documents.
Create a {payload.document_type} titled "{payload.title}".
User requirements:
{payload.requirements}

Additional user context:
{payload.extra_context or "None supplied"}

Retrieved reference context (use only if relevant; do not invent facts):
{context or "No matching local reference text was found."}

Write a polished document with useful headings and coherent paragraphs.
If information is missing, use a clearly marked placeholder instead of inventing it.
"""
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=180,
        )
        response.raise_for_status()
        content = response.json().get("response", "").strip()
        if not content:
            raise HTTPException(status_code=502, detail="The AI model returned an empty response.")
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Cannot reach Ollama at {OLLAMA_URL}. Start Ollama and ensure model '{OLLAMA_MODEL}' is installed. Details: {exc}",
        )
    item = {
        "id": datetime.now().strftime("%Y%m%d%H%M%S%f"),
        "title": payload.title,
        "document_type": payload.document_type,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "content": content,
    }
    save_history(item)
    return {"content": content, "retrieved_context": bool(context), "history_item": item}

@app.post("/api/export/pdf")
def export_pdf(payload: ExportRequest):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    left, y = 50, height - 55
    pdf.setTitle(payload.title)
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(left, y, payload.title[:85])
    y -= 32
    pdf.setFont("Helvetica", 10)
    for paragraph in payload.content.splitlines():
        words = paragraph.split()
        line = ""
        for word in words:
            candidate = (line + " " + word).strip()
            if pdf.stringWidth(candidate, "Helvetica", 10) > width - 100:
                pdf.drawString(left, y, line)
                y -= 15
                line = word
                if y < 55:
                    pdf.showPage()
                    pdf.setFont("Helvetica", 10)
                    y = height - 55
            else:
                line = candidate
        if line:
            pdf.drawString(left, y, line)
            y -= 15
        y -= 5
        if y < 55:
            pdf.showPage()
            pdf.setFont("Helvetica", 10)
            y = height - 55
    pdf.save()
    buffer.seek(0)
    filename = re.sub(r"[^A-Za-z0-9_-]+", "_", payload.title).strip("_") or "document"
    return StreamingResponse(
        buffer, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}.pdf"'},
    )

@app.post("/api/export/docx")
def export_docx(payload: ExportRequest):
    doc = Document()
    doc.add_heading(payload.title, 0)
    for paragraph in payload.content.splitlines():
        if paragraph.strip():
            if paragraph.strip().startswith("#"):
                doc.add_heading(paragraph.strip("# ").strip(), level=1)
            else:
                doc.add_paragraph(paragraph)
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    filename = re.sub(r"[^A-Za-z0-9_-]+", "_", payload.title).strip("_") or "document"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}.docx"'},
    )
