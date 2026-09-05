from fastapi import FastAPI

app = FastAPI(title="DocuMind")


@app.get("/test")
async def test():
    return {"status": "ok", "message": "Server attivo"}