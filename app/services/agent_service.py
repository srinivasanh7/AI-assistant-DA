"""Agent service for AI-powered metadata generation and relationship inference."""

import time
from typing import Any, Dict

from langchain_core.prompts import ChatPromptTemplate

from ..config.settings import get_settings
from .llm_provider import get_configured_llm
from ..models.schemas import AgentInput, LogisticsDataSchema , DatasetMetadata, FilteredDatasetMetadata
from ..prompts.metadata_prompts import METADATA_SYSTEM_PROMPT, METADATA_USER_PROMPT_TEMPLATE, UPDATE_METADATA_SYSTEM_PROMPT, UPDATE_METADATA_USER_PROMPT_TEMPLATE
from ..prompts.relationship_prompts import RELATIONSHIP_SYSTEM_PROMPT, RELATIONSHIP_USER_PROMPT_TEMPLATE
from ..utils.validation_utils import format_input_payload, validate_json_content


class AgentService:
    """Service for AI-powered metadata generation and relationship inference."""

    def __init__(self, settings=None):
        """Initialize the agent service."""
        self.settings = settings or get_settings()
        self.settings.validate_current_provider_key()
        self._metadata_cache = {}

    def _get_llm(self):
        """Get configured LLM instance."""
        return get_configured_llm(self.settings)

    def generate_metadata(self, agent_input: AgentInput) -> Dict[str, Any]:
        """
        Generate metadata JSON using AI agent.
        
        Args:
            agent_input: Input data for the agent
            
        Returns:
            Generated metadata as dictionary
        """
        print(f"  🤖 Initializing LLM...")
        llm_start = time.time()
        llm = self._get_llm()
        llm_with_str_out = llm.with_structured_output(DatasetMetadata)
        llm_init_time = time.time() - llm_start
        print(f"  🤖 LLM initialized in {llm_init_time:.3f}s")

        print(f"  📝 Setting up prompt template...")
        prompt_start = time.time()
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", METADATA_SYSTEM_PROMPT),
                ("user", METADATA_USER_PROMPT_TEMPLATE),
            ]
        )

        input_payload = format_input_payload(agent_input.dict())
        chain = prompt | llm_with_str_out
        prompt_time = time.time() - prompt_start
        print(f"  📝 Prompt prepared in {prompt_time:.3f}s")

        print(f"  🚀 Invoking LLM for metadata generation...")
        invoke_start = time.time()
        result = chain.invoke({"input_payload": input_payload})
        invoke_time = time.time() - invoke_start
        print(f"  🚀 LLM invocation completed in {invoke_time:.3f}s")
        
        return result.dict()
        # content = result.content if hasattr(result, "content") else str(result)
        # return validate_json_content(content)
    
    def update_metadata_descriptions(self, filtered_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
            Update metadata descriptions based on agent queries and user answers using LLM.
            
            Args:
                filtered_metadata: Dictionary containing filtered metadata with agent_query and user_answer pairs
                
            Returns:
                Updated metadata dictionary with improved descriptions
        """
        # Check if there are any columns with agent_query/user_answer to process
        # columns_to_update = [
        #     col for col in filtered_metadata.get('columns', []) 
        #     if 'agent_query' in col and 'user_answer' in col and col.get('user_answer', '').strip()
        # ]
        print("A"*10)
        columns_to_update = [
            col for col in filtered_metadata.get('columns', []) 
            if col.get('agent_query') and col.get('user_answer')
        ]


        print('#'*40)
        print(f"Columns to update: {columns_to_update}")
        # If no columns need updating, return the original metadata (cleaned of agent_query/user_answer)
        if not columns_to_update:
            cleaned_metadata = {
                'dataset_description': filtered_metadata.get('dataset_description', ''),
                'columns': []
            }
            
            for col in filtered_metadata.get('columns', []):
                cleaned_col = {k: v for k, v in col.items() if k not in ['agent_query', 'user_answer']}
                cleaned_metadata['columns'].append(cleaned_col)
            
            print('#'*40)
            print("No columns to update, returning cleaned metadata:", cleaned_metadata)
                
            return cleaned_metadata
        
        # Get LLM and set up structured output
        llm = self._get_llm()
        llm_with_str_out = llm.with_structured_output(FilteredDatasetMetadata)

        # Create the prompt template
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", UPDATE_METADATA_SYSTEM_PROMPT),
                ("user", UPDATE_METADATA_USER_PROMPT_TEMPLATE),
            ]
        )

        # # Format the metadata payload
        # metadata_payload = format_metadata_payload(filtered_metadata)
        
        # Create and invoke the chain
        chain = prompt | llm_with_str_out
        result = chain.invoke({"metadata_payload": filtered_metadata})
        
        return result.dict()

    def infer_relationships(self, final_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Infer inter-column/entity relationships from metadata using AI.
        
        Args:
            final_metadata: Final metadata after user corrections
            
        Returns:
            Inferred relationships as dictionary
        """
        llm = self._get_llm()
        llm_structured = llm.with_structured_output(LogisticsDataSchema)

        final_metadata_json = format_input_payload(final_metadata)
        user_prompt = RELATIONSHIP_USER_PROMPT_TEMPLATE.format(
            final_metadata_json=final_metadata_json
        )

        result = llm_structured.invoke([
            {"role": "system", "content": RELATIONSHIP_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ])

        # Convert Pydantic model to dictionary
        return result.dict()


# Convenience functions for backward compatibility
def generate_metadata_json(agent_input: Dict[str, Any]) -> Dict[str, Any]:
    """Generate metadata JSON using the agent service."""
    service = AgentService()
    # Convert dict to AgentInput if needed
    if isinstance(agent_input, dict):
        agent_input = AgentInput(**agent_input)
    return service.generate_metadata(agent_input)


def infer_relationships_from_metadata(final_metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Infer relationships from metadata using the agent service."""
    service = AgentService()
    return service.infer_relationships(final_metadata)
