from fastapi import FastAPI

app = FastAPI(
    title="CETWorkOverTime API",
    version="3.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)


@app.get("/api/v1/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}
