from fastapi import FastAPI

app = FastAPI(title="Split Money API")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
