"""
Simple FastAPI test server
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import uvicorn

app = FastAPI(title="Upwork DNA API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class QueueItem(BaseModel):
    keyword: str
    status: str = "pending"
    priority: int = 0

# In-memory storage
queue = []

@app.get("/")
async def root():
    return {"message": "Upwork DNA API", "version": "1.0.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/status")
async def status():
    return {
        "queue_count": len(queue),
        "active_jobs": 0,
        "uptime": "0s"
    }

@app.post("/queue")
async def add_to_queue(item: QueueItem):
    queue.append(item)
    return {"ok": True, "message": "Added to queue"}

@app.get("/queue")
async def get_queue():
    return {"items": queue, "count": len(queue)}

@app.post("/scrape")
async def start_scraping(request: dict):
    keyword = request.get("keyword", "")
    # Mock scraping response
    return {
        "job_id": f"job_{keyword}_{hash(keyword)}",
        "keyword": keyword,
        "status": "running",
        "message": f"Scraping started for '{keyword}'"
    }

@app.get("/results")
async def get_results():
    # Mock results
    return {
        "jobs": [],
        "talent": [],
        "projects": [],
        "total": 0
    }

if __name__ == "__main__":
    print("🚀 Starting Upwork DNA API...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
