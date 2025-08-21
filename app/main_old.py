from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Any, Dict
import os

from .profiling import profile_dataset
from .agent import generate_metadata_json, infer_relationships_from_metadata


class AnalyzeRequest(BaseModel):
    file_path: str


class FinalizeMetadataRequest(BaseModel):
    dataset_name: str
    final_metadata: Dict[str, Any]


app = FastAPI(title="AI-Powered Logistics Assistant (Phase 1)")


@app.post("/v1/analyze")
def analyze_dataset(request: AnalyzeRequest):
    file_path = request.file_path
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    try:
        initial_analysis, agent_input = profile_dataset(file_path)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to profile dataset: {exc}") from exc

    try:
        generated_metadata = generate_metadata_json(agent_input)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to generate metadata: {exc}") from exc

    response_body = {
        "dataset_name": os.path.basename(file_path),
        "initial_analysis": initial_analysis,
        "generated_metadata": generated_metadata,
    }
    return JSONResponse(content=response_body)


@app.post("/v1/metadata/finalize")
def finalize_metadata(request: FinalizeMetadataRequest):
    dataset_name = request.dataset_name
    final_metadata = request.final_metadata

    os.makedirs("metadata", exist_ok=True)
    output_path = os.path.join("metadata", f"{dataset_name}_metadata.json")

    try:
        import json

        # Ensure canonical schema contains dataset_name
        to_save = dict(final_metadata)
        to_save.setdefault("dataset_name", dataset_name)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(to_save, f, ensure_ascii=False, indent=2)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to save metadata: {exc}") from exc

    # Infer and persist relationships
    try:
        relationships = infer_relationships_from_metadata(final_metadata)
    except Exception as exc:  # noqa: BLE001
        # Still return success for metadata save, but include error details for relationships
        return JSONResponse(
            content={
                "status": "partial_success",
                "message": f"Metadata saved but failed to infer relationships: {exc}",
                "file_path": output_path,
            }
        )

    rel_path = os.path.join("metadata", f"{dataset_name}_relationships.json")
    try:
        import json
        print('#'*40)
        print('imported json and ready to fill infer relationship')
        with open(rel_path, "w", encoding="utf-8") as f:
            json.dump(relationships, f, ensure_ascii=False, indent=2)
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            content={
                "status": "partial_success",
                "message": f"Metadata saved but failed to persist relationships: {exc}",
                "file_path": output_path,
            }
        )

    return JSONResponse(
        content={
            "status": "success",
            "message": f"Metadata and inferred relationships for {dataset_name} have been saved.",
            "metadata_file_path": output_path,
            "relationships_file_path": rel_path,
            "inferred_relationships": relationships,
        }
    )

