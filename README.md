# DocuAI — AI-Powered Document Generator

A starter implementation based on the architecture described in the project report:
React + Vite frontend, Python FastAPI backend, retrieval-augmented generation (RAG),
Ollama/Llama 3.2 integration, and PDF/DOCX export.

> This is a clean starter package, not a copy of the original GitHub repository.
> The repository URL in the report could not be opened during this session. Review,
> run, and customize this code before submitting it as your own project.

## Requirements
- Python 3.10+
- Node.js 18+
- Ollama installed locally (for AI generation)

## 1. Start Ollama
Install Ollama, then run:

```bash
ollama pull llama3.2
ollama serve
```

## 2. Start the backend

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

Backend: http://127.0.0.1:8000  
API docs: http://127.0.0.1:8000/docs

On macOS/Linux use `cp .env.example .env` instead of `copy`.

## 3. Start the frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite (normally http://localhost:5173).

## RAG knowledge sources
Put `.txt` files in `backend/knowledge/`. The backend uses TF-IDF retrieval to find
relevant text passages and adds them to the Llama 3.2 prompt. This is a lightweight
local vectorization/retrieval implementation suitable for a student demo.

## Features
- Create documents from a title, document type, and requirements
- Retrieve relevant context from local knowledge text files
- Generate content using Ollama's Llama 3.2 model
- Edit generated content in the browser
- Export the edited content as PDF or DOCX
- View recent generation history (stored in a local JSON file)

## Important notes
- The AI generation endpoint requires Ollama to be running.
- If no knowledge files exist, generation still works with the user's prompt.
- Do not commit secrets, private documents, `.env` files, or personal data.
- Add screenshots and test evidence from your own running application before submission.
