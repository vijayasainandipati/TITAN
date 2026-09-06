"""
TITAN API — Ablation Benchmark & Research Validation Endpoints
"""

import os
import json
from fastapi import APIRouter
from evaluation.ablation_runner import run_full_ablation_study
from evaluation.cmapss_pretrain import run_cmapss_prevalidation
from evaluation.leave_engine_out import run_leave_engine_out_evaluation

router = APIRouter(prefix="/api/ablation", tags=["ablation"])


@router.get("/results")
def get_ablation_results():
    """
    Returns comparative evaluation metrics for all 5 ablation variants (A -> E).
    """
    cache_path = os.path.join("data", "ablation_results.json")
    if os.path.exists(cache_path):
        with open(cache_path, "r") as f:
            return json.load(f)
            
    # If not cached, run study and return
    return run_full_ablation_study()


@router.get("/cmapss")
def get_cmapss_prevalidation():
    """
    Returns Phase 0 turbofan benchmark sequence architecture validation results.
    """
    return run_cmapss_prevalidation()


@router.get("/leave_engine_out")
def get_leave_engine_out_results():
    """
    Returns leave-engine-out cross-validation results across distinct engine instances.
    """
    return run_leave_engine_out_evaluation(num_engines=5)
