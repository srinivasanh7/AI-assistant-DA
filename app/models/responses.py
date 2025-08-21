"""Response models for API endpoints."""

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class DatasetSize(BaseModel):
    """Model for dataset size information."""
    rows: int = Field(..., description="Number of rows in the dataset")
    columns: int = Field(..., description="Number of columns in the dataset")


class MissingValueInfo(BaseModel):
    """Model for missing value information."""
    column_name: str = Field(..., description="Name of the column")
    missing_count: int = Field(..., description="Number of missing values")
    missing_percentage: float = Field(..., description="Percentage of missing values")


class TypeCorrectionSuggestion(BaseModel):
    """Model for type correction suggestions."""
    column_name: str = Field(..., description="Name of the column")
    current_type: str = Field(..., description="Current data type")
    suggested_type: str = Field(..., description="Suggested data type")
    confidence: float = Field(..., description="Confidence score for the suggestion")
    reason: str = Field(..., description="Reason for the suggestion")
    sample_values: List[Any] = Field(..., description="Sample values from the column")
    sample_converted: Optional[List[Any]] = Field(None, description="Sample converted values")


class DataQualityReport(BaseModel):
    """Model for data quality report."""
    missing_values: List[MissingValueInfo] = Field(..., description="Missing value information")
    type_correction_suggestions: List[TypeCorrectionSuggestion] = Field(..., description="Type correction suggestions")
    statistics: Dict[str, Any] = Field(..., description="Descriptive statistics")


class InitialAnalysis(BaseModel):
    """Model for initial dataset analysis."""
    size: DatasetSize = Field(..., description="Dataset size information")
    data_quality_report: DataQualityReport = Field(..., description="Data quality report")


class AnalyzeResponse(BaseModel):
    """Response model for dataset analysis endpoint."""
    dataset_name: str = Field(..., description="Name of the dataset")
    initial_analysis: InitialAnalysis = Field(..., description="Initial analysis results")
    generated_metadata: Dict[str, Any] = Field(..., description="AI-generated metadata")


class FinalizeMetadataResponse(BaseModel):
    """Response model for metadata finalization endpoint."""
    status: str = Field(..., description="Status of the operation")
    message: str = Field(..., description="Status message")
    metadata_file_path: Optional[str] = Field(None, description="Path to saved metadata file")
    relationships_file_path: Optional[str] = Field(None, description="Path to saved relationships file")
    inferred_relationships: Optional[Dict[str, Any]] = Field(None, description="Inferred relationships")
