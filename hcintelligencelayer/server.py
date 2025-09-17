from fastapi import FastAPI
from agents.v1.fallpredictionagent.agent import router as fallpredictionagent_router
from agents.v1.tripplanneragent.agent import router as tripplanneragent_router

# --- FastAPI App ---
app = FastAPI(
    title="Agent service", 
    version="1.0.0", 
    docs_url="/docs",
    redoc_url=None,
)
app.include_router(fallpredictionagent_router, prefix="/agents/v1/fallpredictionagent", tags=["fallpredictionagent"])
app.include_router(tripplanneragent_router, prefix="/agents/v1/tripplanneragent", tags=["tripplanneragent"])
