"""API routes for the logistics assistant."""

import os
import time
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, UploadFile, Request
from fastapi.responses import JSONResponse

from ..models.requests import FinalizeMetadataRequest
from ..models.responses import AnalyzeResponse, FinalizeMetadataResponse
from ..services.agent_service import AgentService
from ..services.profiling_service import ProfilingService
from ..utils.file_utils import (
    get_filename_without_extension,
    get_metadata_file_path,
    get_relationships_file_path,
    save_json_file,
    ensure_directory_exists,
    convert_csv_to_parquet
)
from ..utils.data_utils import filter_required_columns

router = APIRouter()


async def handle_file_upload(uploaded_file: UploadFile) -> str:
    """
    Handle CSV file upload and return the saved file path.

    Args:
        uploaded_file: The uploaded file from FastAPI

    Returns:
        str: Path to the saved file

    Raises:
        HTTPException: If file validation fails
    """
    # Validate file type
    if not uploaded_file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    if not uploaded_file.filename.lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")

    # Validate file size (50MB limit)
    if uploaded_file.size and uploaded_file.size > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size too large. Maximum 50MB allowed")

    # Create uploads directory if it doesn't exist
    uploads_dir = "uploads"
    ensure_directory_exists(uploads_dir)

    # Generate safe filename with timestamp to avoid conflicts
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Sanitize filename - remove any path separators and special characters
    safe_base_name = "".join(c for c in uploaded_file.filename if c.isalnum() or c in "._-")
    safe_filename = f"{timestamp}_{safe_base_name}"
    file_path = os.path.join(uploads_dir, safe_filename)

    try:
        # Save uploaded file
        with open(file_path, "wb") as buffer:
            content = await uploaded_file.read()
            if not content:
                raise HTTPException(status_code=400, detail="Uploaded file is empty")
            buffer.write(content)

        print(f"📁 File uploaded successfully: {file_path}")
        return file_path

    except Exception as e:
        # Clean up partial file if something went wrong
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {str(e)}")


@router.post("/v1/analyze", response_model=AnalyzeResponse)
async def analyze_dataset(request: Request):
    """
    Analyze a dataset and generate initial profiling and AI metadata.

    Supports two methods:
    1. JSON body: {"file_path": "path/to/file.csv"}
    2. Form data: uploaded_file as multipart/form-data

    Returns:
        Analysis response with profiling data and generated metadata
    """
    content_type = request.headers.get("content-type", "")
    print(f"🔍 Analyze request received - Content-Type: {content_type}")

    file_path = None
    uploaded_file = None

    try:
        if content_type.startswith("application/json"):
            # Handle JSON request (existing method)
            body = await request.json()
            file_path = body.get("file_path")

            if not file_path:
                raise HTTPException(
                    status_code=400,
                    detail="'file_path' is required in JSON body"
                )

            print(f"📂 Processing existing file: {file_path}")

            # Validate existing file path
            if not os.path.exists(file_path):
                raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

        elif content_type.startswith("multipart/form-data"):
            # Handle form data request (file upload)
            form = await request.form()
            uploaded_file = form.get("uploaded_file")

            if not uploaded_file:
                raise HTTPException(
                    status_code=400,
                    detail="'uploaded_file' is required in form data"
                )

            print(f"📁 Processing uploaded file: {uploaded_file.filename}")

            # Handle file upload
            file_path = await handle_file_upload(uploaded_file)

        else:
            raise HTTPException(
                status_code=400,
                detail="Content-Type must be 'application/json' or 'multipart/form-data'"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to parse request: {str(e)}"
        )

    try:
        analysis_start_time = time.time()
        print(f"📊 Starting analysis for file: {file_path} at {time.strftime('%H:%M:%S')}")

        # Initialize services
        init_start = time.time()
        profiling_service = ProfilingService()
        agent_service = AgentService()
        init_time = time.time() - init_start
        print(f"🔧 Services initialized in {init_time:.3f}s")

        # Perform dataset profiling
        profiling_start = time.time()
        initial_analysis, agent_input = profiling_service.profile_dataset(file_path)
        profiling_time = time.time() - profiling_start
        print(f"📈 Dataset profiling completed in {profiling_time:.3f}s")

        # Generate metadata using AI
        ai_start = time.time()
        generated_metadata = agent_service.generate_metadata(agent_input)
        ai_time = time.time() - ai_start
        print(f"🤖 AI metadata generation completed in {ai_time:.3f}s")

        response_data = {
            "dataset_name": os.path.basename(file_path),
            "initial_analysis": initial_analysis,
            "generated_metadata": generated_metadata,
        }

        total_time = time.time() - analysis_start_time
        print("returned json resposne at /v1/analyze",response_data)
        print(f"✅ Analysis completed successfully for: {os.path.basename(file_path)}")
        print(f"⏱️ Total analysis time: {total_time:.3f}s (Profiling: {profiling_time:.3f}s, AI: {ai_time:.3f}s)")
        return JSONResponse(content=response_data)

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as exc:
        print(f"❌ Analysis failed: {str(exc)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze dataset: {str(exc)}"
        ) from exc


@router.post("/v1/metadata/finalize", response_model=FinalizeMetadataResponse)
def finalize_metadata(request: FinalizeMetadataRequest):
    """
    Finalize and save user-corrected metadata with relationship inference.
    
    Args:
        request: Finalization request with dataset name and final metadata
        
    Returns:
        Response with save status and inferred relationships
    """
    dataset_name = request.dataset_name
    final_metadata = request.final_metadata
    
    print("request payload at /v1/metadata/finalize",request)

    try:
        
        # Initialize agent service for relationship inference and metadata prep
        agent_service = AgentService()
        metadata_collected = dict(final_metadata)
        print('#'*40)
        print("The obtained metadata is", metadata_collected)
        # Filter columns where required = 'true'
        filtered_columns = [
            column for column in metadata_collected['columns'] 
            if column.get('required') == 'true'
        ]
        filtered_columns_names = [col['column_name'] for col in filtered_columns]
        print('#'*40)
        print("The filtered columns are:", filtered_columns)
        filtered_metadata = filter_required_columns(metadata_collected, filtered_columns)
        print('#'*40)
        print("The filtered metadata is", filtered_metadata)
        metadata_to_save = agent_service.update_metadata_descriptions(filtered_metadata)
        metadata_to_save.setdefault("dataset_name", dataset_name)
        # Save metadata
        metadata_file_path = get_metadata_file_path(dataset_name)
        save_json_file(metadata_to_save, metadata_file_path)
        # Save the required columns to a parquet file.
        convert_csv_to_parquet(dataset_name=dataset_name, filtered_columns= filtered_columns_names)
        
        try:
            # Infer and persist relationships
            relationships = agent_service.infer_relationships(metadata_to_save)
            relationships_file_path = get_relationships_file_path(dataset_name)
            save_json_file(relationships, relationships_file_path)
            
            return JSONResponse(
                content={
                    "status": "success",
                    "message": f"Metadata and inferred relationships for {dataset_name} have been saved.",
                    "metadata_file_path": metadata_file_path,
                    "relationships_file_path": relationships_file_path,
                    "inferred_relationships": relationships,
                }
            )
            
        except Exception as rel_exc:
            # Still return success for metadata save, but include error details for relationships
            return JSONResponse(
                content={
                    "status": "partial_success",
                    "message": f"Metadata saved but failed to infer relationships: {str(rel_exc)}",
                    "metadata_file_path": metadata_file_path,
                }
            )
            
    except Exception as exc:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to save metadata: {str(exc)}"
        ) from exc


