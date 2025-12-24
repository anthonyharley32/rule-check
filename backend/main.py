"""FastAPI application for NFHS Rules Chat API."""

import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from functions.chat import ChatService

app = FastAPI(
    title="NFHS Rules Chat API",
    description="Chat API for NFHS Basketball Rules with citations",
    version="0.1.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

chat_service = ChatService()


class ChatRequest(BaseModel):
    """Request body for chat endpoint."""
    question: str
    top_k: int = 5


class ChatResponse(BaseModel):
    """Response body for non-streaming chat."""
    answer: str
    citations: list[dict]


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Non-streaming chat endpoint."""
    try:
        answer, citations = chat_service.chat(
            question=request.question,
            top_k=request.top_k
        )
        return ChatResponse(
            answer=answer,
            citations=[
                {
                    "ref_num": c.ref_num,
                    "source_ref": c.source_ref,
                    "content_preview": c.content_preview
                }
                for c in citations
            ]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Streaming chat endpoint."""

    def generate():
        try:
            for event in chat_service.chat_stream(
                question=request.question,
                top_k=request.top_k
            ):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
