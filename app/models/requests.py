"""Request models for API endpoints."""

from pydantic import BaseModel, Field
from typing import Any, Dict


class AnalyzeRequest(BaseModel):
    """Request model for dataset analysis endpoint."""
    file_path: str = Field(..., description="Path to the CSV file to analyze")


class FinalizeMetadataRequest(BaseModel):
    """Request model for metadata finalization endpoint."""
    dataset_name: str = Field(..., description="Name of the dataset")
    final_metadata: Dict[str, Any] = Field(..., description="Final metadata after user corrections")
