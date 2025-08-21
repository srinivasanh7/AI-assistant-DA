from __future__ import annotations

import json
import os
from typing import Any, Dict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# Load environment variables from .env if present
load_dotenv()


SYSTEM_PROMPT = (
    "You are a world-class Senior Transportation Logistics Analyst with 20 years of "
    "experience. Your expertise lies in quickly understanding complex logistics datasets. "
    "You are meticulous, detail-oriented, and your goal is to create clear, unambiguous, "
    "and structured metadata for a new dataset. You think step-by-step to deconstruct "
    "column names, infer their business meaning, and classify them correctly."
)


USER_PROMPT_TEMPLATE = (
    "Objective: Analyze the provided dataset schema and sample data to generate a "
    "comprehensive metadata JSON object.\n"
    "Your Persona: Senior Transportation Logistics Analyst.\n"
    "Input Data: {input_payload}\n\n"
    "Instructions:\n"
    "1. Write a brief, high-level dataset_description explaining what the dataset likely represents.\n"
    "2. Iterate through each column provided in the columns list.\n"
    "3. For each column, create a JSON object with the following keys:\n"
    "   - column_name: The exact name of the column.\n"
    "   - description: A clear, business-friendly description. Example: For Distance_km, describe it as 'The total distance of the trip in kilometers.'\n"
    "   - data_type: Classify the column into one of these specific types: 'Numerical', 'Categorical', 'Datetime', 'ID', 'Text', 'Boolean'. Be smart about this; a column like OnTimeDelivery with values 0 and 1 is 'Boolean'. Duration_min with string numbers is 'Numerical'.\n"
    "   - categorical_values: If and only if the data_type is 'Categorical', this key must be present. It should be an array of objects, where you provide a value and a description for each unique value provided in the input. Example: For ServiceType value 2W, the description should be '2 Wheeler Vehicle'.\n\n"
    "Output Format:\n"
    "You MUST respond with a single, valid JSON object. Do not include any text or explanations outside of the JSON structure.\n"
    "The JSON MUST have the following top-level keys: dataset_description (string) and columns (array)."
)


def _format_input_payload(agent_input: Dict[str, Any]) -> str:
    # Render as compact JSON string to place inside the prompt
    return json.dumps(agent_input, ensure_ascii=False, indent=2)


def generate_metadata_json(agent_input: Dict[str, Any]) -> Dict[str, Any]:
    # Ensure API key is available from environment/.env
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Create a .env file with OPENAI_API_KEY=<your_key>."
        )

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("user", USER_PROMPT_TEMPLATE),
        ]
    )

    input_payload = _format_input_payload(agent_input)
    chain = prompt | llm
    result = chain.invoke({"input_payload": input_payload})

    content = result.content if hasattr(result, "content") else str(result)

    # Parse JSON strictly; attempt a basic brace-extraction fallback if needed
    try:
        return json.loads(content)
    except Exception:  # noqa: BLE001
        try:
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(content[start : end + 1])
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Model did not return valid JSON: {exc}") from exc

    # If parsing still fails, raise a generic error
    raise RuntimeError("Model did not return valid JSON.")



# =====================
# Relationship Inference
# =====================

RELATIONSHIP_SYSTEM_PROMPT = (
    "You are a senior Logistics Data Architect. You design clean entity-relationship models "
    "from dataset metadata. Your job is to: (1) group columns into business entities, (2) "
    "identify keys and foreign-keys, (3) infer directed relationships between entities, and "
    "(4) cluster operational/metric columns that co-explain performance (e.g., on_time_delivery, "
    "cancelled, extra_time_on_delivery).\n\n"
    "Rules:\n"
    "- Prefer entity names like driver, vehicle, route, order, stop, shipment, hub, customer, performance.\n"
    "- Keys often end with _id, code, number; foreign-keys reference another entity's key.\n"
    "- Relationship cardinality: one-to-one, one-to-many, many-to-one, many-to-many (rare without bridge).\n"
    "- Metrics/outcomes often Boolean or Numerical rate/count/duration columns. Group related outcomes together.\n"
    "- Output strictly in the required JSON schema (no extra text).\n\n"
)



RELATIONSHIP_USER_PROMPT_TEMPLATE = (
    "Using the UPDATED METADATA below, infer entities, relationships, and metric groupings.\n"
    "Return strictly valid JSON in the schema defined earlier.\n\n"
    "UPDATED METADATA:\n{final_metadata_json}"
)

from typing import List, Literal
from pydantic import BaseModel, Field


class Entity(BaseModel):
    """Represents a data entity extracted from logistics CSV metadata."""
    name: str = Field(..., description="Name of the entity")
    columns: List[str] = Field(..., description="List of column names belonging to this entity")
    keys: List[str] = Field(..., description="List of key columns (primary/foreign keys) for this entity")
    type: Literal['core', 'dimension', 'metric_container'] = Field(
        ..., 
        description="Type of entity: core (main business objects), dimension (lookup/reference data), or metric_container (aggregated metrics)"
    )


class EntityRelationship(BaseModel):
    """Represents a relationship between two entities."""
    source: str = Field(..., description="Source entity name")
    target: str = Field(..., description="Target entity name")
    cardinality: Literal['one-to-one', 'one-to-many', 'many-to-one', 'many-to-many'] = Field(
        ..., 
        description="Relationship cardinality between source and target entities"
    )
    on: List[str] = Field(..., description="List of column names that define the relationship (join keys)")


class MetricRelationship(BaseModel):
    """Represents relationships between metric columns that can be grouped together."""
    group: str = Field(..., description="Name or identifier for the metric group")
    columns: List[str] = Field(..., description="List of related metric column names")
    rationale: str = Field(..., description="Explanation of why these metrics are related or grouped together")


class LogisticsDataSchema(BaseModel):
    """Main schema for logistics data structure inference output."""
    entities: List[Entity] = Field(..., description="List of identified entities in the logistics data")
    entity_relationships: List[EntityRelationship] = Field(..., description="List of relationships between entities")
    metric_relationships: List[MetricRelationship] = Field(..., description="List of metric groupings and their relationships")

    class Config:
        # Ensure all fields are required
        validate_all = True
        # Allow extra fields to be ignored if present
        extra = "forbid"

def infer_relationships_from_metadata(final_metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Infer inter-column/entity relationships from updated metadata using an LLM.

    Returns a JSON-compatible dict matching LogisticsDataSchema schema.
    """
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Create a .env file with OPENAI_API_KEY=<your_key>."
        )
    #structured output:
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    llm_structured = llm.with_structured_output(LogisticsDataSchema)


    final_metadata_json = json.dumps(final_metadata, ensure_ascii=False, indent=2)
    system_prompt = RELATIONSHIP_SYSTEM_PROMPT
    user_prompt = RELATIONSHIP_USER_PROMPT_TEMPLATE.format( final_metadata_json = final_metadata_json)

    result = llm_structured.invoke([
        {"role":"system", "content": system_prompt},
        {"role": "user", "content": user_prompt}])
    print(f"Classification result:", result)
    # Convert Pydantic model to dictionary
    return result.dict()

   