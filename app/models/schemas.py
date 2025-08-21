"""Data schemas for logistics analysis."""

from pydantic import BaseModel, Field
from typing import List, Literal, Dict, Any, Optional


class CategoricalValue(BaseModel):
    """Model for categorical value descriptions."""
    value: str = Field(..., description="The categorical value")
    description: str = Field(..., description="Description of the categorical value")


class ColumnMetadata(BaseModel):
    """Contains the complete analytical metadata for a single column, including its
    relevance classification, description, and any clarifying questions for the user."""
    column_name: str = Field(..., description="The exact Name of the column")
    required: Literal["true", "unclear","false"] = Field(
        ..., 
        description="The agent's confidence in the column's relevance. 'true' for relevant, 'false' for irrelevant and 'unclear' for ambiguous. "
    )
    description: str = Field(..., description="Description of what the column represents")
    data_type: Literal['Numerical', 'Categorical', 'Datetime', 'ID', 'Text', 'Boolean'] = Field(
        ..., description="Standardized data type classification"
    )
    categorical_values: Optional[List[CategoricalValue]] = Field(
        None, description="Descriptions for categorical values (only for categorical columns),only if they are unamiguous."
    )
    agent_query: Optional[str] = Field(
        default=None, 
        description="(Optional) A question for the user if the column's description or its context or the meaning of its values are ambiguous."
    )
    
    user_answer: Optional[str] = Field(
        default=None, 
        description="(Optional) A placeholder (empty string) for the user's response to the agent_query. Must be present if agent_query exists."
    )


class DatasetMetadata(BaseModel):
    """Model for complete dataset metadata."""
    dataset_name: str = Field(..., description="Name of the dataset")
    dataset_description: str = Field(..., description="High-level description of the dataset")
    columns: List[ColumnMetadata] = Field(..., description="Metadata for each column")

class FilteredDatasetMetadata(BaseModel):
    """Model for filtered dataset metadata."""
    dataset_description: str = Field(..., description="High-level description of the dataset")
    columns: List[ColumnMetadata] = Field(..., description="Metadata for each column after considering user's response")


class Entity(BaseModel):
    """Model for data entities in logistics analysis."""
    name: str = Field(..., description="Name of the entity")
    columns: List[str] = Field(..., description="List of column names belonging to this entity")
    keys: List[str] = Field(..., description="List of key columns (primary/foreign keys) for this entity")
    type: Literal['core', 'dimension', 'metric_container'] = Field(
        ..., 
        description="Type of entity: core (main business objects), dimension (lookup/reference data), or metric_container (aggregated metrics)"
    )


class EntityRelationship(BaseModel):
    """Model for relationships between entities."""
    source: str = Field(..., description="Source entity name")
    target: str = Field(..., description="Target entity name")
    cardinality: Literal['one-to-one', 'one-to-many', 'many-to-one', 'many-to-many'] = Field(
        ..., 
        description="Relationship cardinality between source and target entities"
    )
    on: List[str] = Field(..., description="List of column names that define the relationship (join keys)")


class MetricRelationship(BaseModel):
    """Model for relationships between metric columns."""
    group: str = Field(..., description="Name or identifier for the metric group")
    columns: List[str] = Field(..., description="List of related metric column names")
    rationale: str = Field(..., description="Explanation of why these metrics are related or grouped together")


class LogisticsDataSchema(BaseModel):
    """Model for complete logistics data structure inference."""
    entities: List[Entity] = Field(..., description="List of identified entities in the logistics data")
    entity_relationships: List[EntityRelationship] = Field(..., description="List of relationships between entities")
    metric_relationships: List[MetricRelationship] = Field(..., description="List of metric groupings and their relationships")

    class Config:
        validate_default = True
        extra = "forbid"


class AgentInput(BaseModel):
    """Model for agent input data."""
    columns: List[str] = Field(..., description="List of column names")
    column_data_types: Dict[str, str] = Field(..., description="Mapping of column names to data types")
    categorical_unique_values: Dict[str, List[Any]] = Field(..., description="Unique values for categorical columns")
    data_sample: List[Dict[str, Any]] = Field(..., description="Sample rows from the dataset")
