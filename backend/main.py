"""
TITAN Main Application Entry Point
FastAPI service exposing REST and Streaming endpoints for the 5-View Defence Dashboard.
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.api import (
    telemetry_router,
    ablation_router,
    mission_router,
    advisory_router,
    fleet_router
)
from backend.ingestion.stream_handler import fleet_stream_manager

app = FastAPI(
    title="TITAN — Aero-Piston Engine Digital Twin API",
    description="Physics-Informed, Mission-Aware Digital Twin for MALE UAV Aero-Piston Propulsion (DRDO-iDEX SIH 26054)",
    version="1.0.0"
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API route modules
app.include_router(telemetry_router)
app.include_router(ablation_router)
app.include_router(mission_router)
app.include_router(advisory_router)
app.include_router(fleet_router)


@app.on_event("startup")
def startup_event():
    print("\n" + "="*70)
    print("  TITAN DIGITAL TWIN BACKEND INITIALIZED (PORT 8000)")
    print("  Domain: Defence / Aerospace / UAV Propulsion (DRDO-iDEX)")
    print(f"  Simulated Active Fleet: {len(fleet_stream_manager.fleet)} Engines")
    print("="*70 + "\n")
    
    # Ensure data directory exists
    os.makedirs("data/synthetic", exist_ok=True)
    cache_path = os.path.join("data", "ablation_results.json")
    if not os.path.exists(cache_path):
        from evaluation.ablation_runner import run_full_ablation_study
        run_full_ablation_study()


@app.get("/api/health")
def health_check():
    return {
        "status": "HEALTHY",
        "system": "TITAN MALE-UAV Digital Twin Core",
        "active_engine": fleet_stream_manager.active_engine_id,
        "fleet_size": len(fleet_stream_manager.fleet),
        "version": "1.0.0"
    }


# Mount static assets if dashboard dist exists
dist_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dashboard", "dist")
if os.path.exists(dist_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(dist_dir, "assets")), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        index_file = os.path.join(dist_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"message": "TITAN API operational"}
