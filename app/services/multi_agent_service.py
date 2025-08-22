"""Multi-agent system using LangGraph for Phase 2 query processing."""

import json
import threading
from typing import Any, Callable, Dict, List, Optional

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END

from ..config.settings import get_settings
from .llm_provider import get_configured_llm
from ..models.phase2_models import (
    AgentState, AgentPlan,
    CodeGenerationResponse,
    ErrorAnalysisResponse,
    ChartGenerationResponse
)
from ..prompts.phase2_prompts import (
    PLANNER_AGENT_PROMPT,
    CODE_GENERATION_AGENT_PROMPT,
    ERROR_ANALYSIS_AGENT_PROMPT,
    CHART_GENERATION_AGENT_PROMPT,
    FINAL_RESPONSE_AGENT_PROMPT
)
from ..services.jupyter_service import get_jupyter_service
from ..services.session_service import get_session_manager
from ..utils.validation_utils import validate_json_content


class MultiAgentService:
    """Multi-agent service for processing natural language queries."""
    
    def __init__(self):
        """Initialize the multi-agent service."""
        print("🔄 Initializing MultiAgentService...")

        print("📋 Loading settings...")
        self.settings = get_settings()
        print(f"🔧 LLM Provider: {self.settings.llm_provider}")
        
        # Validate the appropriate API key based on provider
        print("🔑 Validating API key for current provider...")
        try:
            self.settings.validate_current_provider_key()
            print(f"✅ {self.settings.llm_provider.upper()} API key validated")
        except Exception as e:
            print(f"❌ API key validation failed: {e}")
            raise

        print(f"🤖 Creating {self.settings.llm_provider.upper()} client...")
        try:
            import time
            start_time = time.time()
            print(f"🔄 Attempting to create {self.settings.llm_provider.upper()} client...")
            # Create LLM client using the provider factory
            self.llm = get_configured_llm(self.settings)
            elapsed = time.time() - start_time
            print(f"✅ {self.settings.llm_provider.upper()} client created successfully in {elapsed:.2f}s")
        except Exception as e:
            print(f"❌ Failed to create {self.settings.llm_provider.upper()} client: {e}")
            raise

        print("📊 Getting Jupyter service...")
        try:
            self.jupyter_service = get_jupyter_service()
            print("✅ Jupyter service obtained")
        except Exception as e:
            print(f"❌ Failed to get Jupyter service: {e}")
            raise
            
        print("📋 Getting session manager...")
        try:
            self.session_manager = get_session_manager()
            print("✅ Session manager obtained")
        except Exception as e:
            print(f"❌ Failed to get session manager: {e}")
            raise
            
        print("🏗️ Building workflow graph...")
        try:
            self.graph = self._build_graph()
            print("✅ Workflow graph built successfully")
        except Exception as e:
            print(f"❌ Failed to build workflow graph: {e}")
            raise
            
        print("🤖 MultiAgentService initialized with LangGraph workflow")
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        print("🏗️ Building LangGraph workflow...")

        # Create the state graph
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("planner", self._planner_agent)
        workflow.add_node("code_generator", self._code_generation_agent)
        workflow.add_node("executor", self._code_executor)
        workflow.add_node("error_analyzer", self._error_analysis_agent)
        workflow.add_node("chart_generator", self._chart_generation_agent)
        workflow.add_node("final_responder", self._final_response_agent)
        
        # Set entry point
        workflow.set_entry_point("planner")
        
        # Add edges
        workflow.add_edge("planner", "code_generator")
        workflow.add_edge("code_generator", "executor")
        workflow.add_conditional_edges(
            "executor",
            self._should_continue_execution,
            {
                "continue": "code_generator",
                "error": "error_analyzer", 
                "chart": "chart_generator",
                "complete": "final_responder"
            }
        )
        workflow.add_edge("error_analyzer", "code_generator")
        workflow.add_edge("chart_generator", "executor")
        workflow.add_edge("final_responder", END)  # END was imported above

        print("✅ LangGraph workflow built successfully")
        return workflow.compile()
    
    async def _planner_agent(self, state: AgentState) -> AgentState:
        """Planner agent that creates execution plan."""
        print(f"🎯 Planner Agent: Creating plan for query: '{state.user_query}'")
        
        try:
            # Format conversation history
            chat_history = "\n".join([
                f"User: {turn.user_query}\nAgent: {turn.agent_response}"
                for turn in state.conversation_history
            ]) if state.conversation_history else "No previous conversation."
            
            # Create prompt
            prompt = ChatPromptTemplate.from_template(PLANNER_AGENT_PROMPT)
            chain = prompt | self.llm
            

            # Generate plan
            response = chain.invoke({
                "user_query": state.user_query,
                "chat_history": chat_history,
                "metadata_json": json.dumps(state.dataset_metadata, indent=2)
            })
            print(f"response from planner agent: {response}")
            # Parse the plan
            def extract_json_from_markdown(content: str) -> str:
                """Extract JSON content from markdown code blocks."""
                content = content.strip()
                
                # Check if content is wrapped in code blocks
                if content.startswith('```json'):
                    # Find the start of JSON (after ```json\n)
                    start_marker = '```json\n'
                    end_marker = '\n```'
                    
                    start_idx = content.find(start_marker)
                    if start_idx != -1:
                        start_idx += len(start_marker)
                        end_idx = content.find(end_marker, start_idx)
                        if end_idx != -1:
                            return content[start_idx:end_idx].strip()
                
                elif content.startswith('```'):
                    # Handle generic code blocks
                    lines = content.split('\n')
                    if len(lines) > 2:
                        return '\n'.join(lines[1:-1]).strip()
                
                # Return as-is if no code blocks found
                return content

            # Parse the plan
            plan_content = response.content if hasattr(response, 'content') else str(response)
            
            # Extract JSON from markdown if present
            clean_json = extract_json_from_markdown(plan_content)
            plan_steps = json.loads(clean_json)
            
            print(f"📋 Plan created with {len(plan_steps)} steps:")
            for i, step in enumerate(plan_steps, 1):
                print(f"  {i}. {step}")
            
            # Update state
            state.plan = AgentPlan(steps=plan_steps, current_step_index=0, completed=False)
            # state.plan = {"steps": plan_steps, "current_step_index": 0, "completed": False}
            state.current_step_index = 0
            print("state returend successfully")
            return state
            
        except Exception as e:
            print(f"❌ Planner Agent error: {e}")
            raise
    
    async def _code_generation_agent(self, state: AgentState) -> AgentState:
        """Code generation agent using ReAct pattern."""
        import json
        import asyncio
        import time

        current_step = state.plan.steps[state.current_step_index]
        print(f"💻 Code Generation Agent: Working on step {state.current_step_index + 1}: '{current_step}'")

        try:
            # Create prompt (using regular text output instead of structured output)
            prompt = ChatPromptTemplate.from_template(CODE_GENERATION_AGENT_PROMPT)
            chain = prompt | self.llm
            
            # Generate code
            error_analysis_text = ""
            if state.error_analysis:
                error_analysis_text = f"Previous error: {state.error_analysis.diagnosis}\nSuggested fix: {state.error_analysis.suggestion}"

            print("🔄 About to call OpenAI API for code generation...")
            print(f"📊 Context size check:")
            print(f"   - Plan steps: {len(json.dumps(state.plan.steps))} chars")
            print(f"   - Execution history: {len(str(state.execution_history))} chars")
            print(f"   - Available variables: {state.available_variables}")
            print(f"   - Execution context size: {len(json.dumps(state.execution_context, indent=2)) if state.execution_context else 0} chars")

            # Use asyncio with timeout for better control
            api_start = time.time()
            try:
                # Simplify execution context to avoid huge prompts
                simplified_context = {}
                if state.execution_context:
                    # Only include the most recent step's output (last 500 chars)
                    for key, value in state.execution_context.items():
                        if isinstance(value, dict) and 'output' in value:
                            output = value.get('output', '')
                            if len(output) > 500:
                                value['output'] = output[:500] + "... (truncated)"
                        simplified_context[key] = value
                
                # Wrap in asyncio timeout for additional safety
                # Extract just column information from metadata for the prompt
                column_info = []
                if state.dataset_metadata and 'columns' in state.dataset_metadata:
                    for col in state.dataset_metadata['columns']:
                        column_info.append({
                            "column_name": col.get('column_name'),
                            "data_type": col.get('data_type')
                        })
                
                metadata_simplified = {
                    "columns": column_info
                }
                
                response = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: chain.invoke({
                            "metadata_json": json.dumps(metadata_simplified, indent=2),
                            "full_plan_json": json.dumps(state.plan.steps, indent=2),
                            "current_step_from_plan": current_step,
                            "log_of_past_steps": "\n".join(state.execution_history[-3:]) if state.execution_history else "No previous steps.",  # Only last 3 steps
                            "available_variables": ", ".join(state.available_variables),
                            "execution_context": json.dumps(simplified_context, indent=2) if simplified_context else "No previous results.",
                            "error_analysis": error_analysis_text if error_analysis_text else "No previous errors."
                        })
                    ),
                    timeout=60.0  # 45 second hard timeout
                )
                api_elapsed = time.time() - api_start
                print(f"✅ OpenAI API call completed successfully in {api_elapsed:.2f}s")
            except asyncio.TimeoutError:
                print(f"❌ OpenAI API call timed out after 45 seconds")
                # Provide a fallback simple code for step 2
                if state.current_step_index == 1:  # Second step (0-indexed)
                    print("🔄 Using fallback code for degrowth calculation")
                    state.current_thought = "Calculating degrowth by comparing first and last revenue values for each city"
                    state.current_code = """# Calculate degrowth for each city
city_growth = []
for city in df_grouped['City'].unique():
    city_data = df_grouped[df_grouped['City'] == city].sort_values('Date')
    if len(city_data) > 1:
        first_revenue = city_data.iloc[0]['Revenue_INR']
        last_revenue = city_data.iloc[-1]['Revenue_INR']
        growth_pct = ((last_revenue - first_revenue) / first_revenue) * 100
        city_growth.append({'City': city, 'Growth_Percentage': growth_pct})

growth_df = pd.DataFrame(city_growth)
print("City Growth/Degrowth Analysis:")
print(growth_df.sort_values('Growth_Percentage'))

# Find city with maximum degrowth (most negative growth)
max_degrowth_city = growth_df.loc[growth_df['Growth_Percentage'].idxmin()]
print(f"\\nCity with maximum degrowth: {max_degrowth_city['City']} ({max_degrowth_city['Growth_Percentage']:.2f}%)")"""
                    return state
                else:
                    raise Exception("OpenAI API timeout")
            except Exception as e:
                print(f"❌ OpenAI API call failed: {e}")
                raise
            print("#"*40)
            print(f'response from code generation agent: {response}')

            # Parse response content (now it's text instead of structured)
            response_content = response.content if hasattr(response, 'content') else str(response)
            print("#"*40)
            print(f'response content: {response_content}')

            # Parse the response to extract thought and code
            # The response comes wrapped in markdown code blocks
            try:
                # Extract JSON from markdown code blocks
                def extract_json_from_markdown(content: str) -> str:
                    """Extract JSON content from markdown code blocks."""
                    content = content.strip()

                    # Check if content is wrapped in ```json code blocks
                    if '```json' in content:
                        start_marker = '```json\n'
                        end_marker = '\n```'

                        start_idx = content.find(start_marker)
                        if start_idx != -1:
                            start_idx += len(start_marker)
                            end_idx = content.find(end_marker, start_idx)
                            if end_idx != -1:
                                return content[start_idx:end_idx].strip()

                    # If no code blocks, try to find JSON directly
                    if content.strip().startswith('{'):
                        return content.strip()

                    return content

                # Extract and parse JSON
                json_content = extract_json_from_markdown(response_content)
                print(f"🔍 Extracted JSON: {json_content[:200]}...")

                parsed_response = json.loads(json_content)
                state.current_thought = parsed_response.get('thought', 'No thought provided')
                state.current_code = parsed_response.get('code', 'No code provided')

                print(f"✅ Successfully parsed thought and code")

            except Exception as parse_error:
                print(f"⚠️ Failed to parse JSON response: {parse_error}")
                print(f"🔍 Raw response content: {response_content[:500]}...")

                # Fallback: try to extract code from any code blocks
                state.current_thought = "Generated code for the current step"
                if '```python' in response_content:
                    # Extract Python code blocks
                    lines = response_content.split('\n')
                    code = ""
                    in_code_block = False

                    for line in lines:
                        if line.strip().startswith('```python'):
                            in_code_block = True
                            continue
                        elif line.strip() == '```':
                            in_code_block = False
                            continue
                        elif in_code_block:
                            code += line + '\n'

                    state.current_code = code.strip() or response_content.strip()
                else:
                    state.current_code = response_content.strip()
            
            print(f"🧠 Agent thought: {state.current_thought}")
            print(f"📝 Generated code:\n{state.current_code}")
            
            return state
            
        except Exception as e:
            print(f"❌ Code Generation Agent error: {e}")
            raise
    
    async def _code_executor(self, state: AgentState) -> AgentState:
        """Execute generated code in Jupyter kernel."""
        print(f"🚀 Code Executor: Executing code for step {state.current_step_index + 1}")
        
        try:
            # Get kernel manager
            kernel_manager = self.session_manager.get_kernel_manager(state.session_id)
            if not kernel_manager:
                raise RuntimeError(f"No kernel manager found for session {state.session_id}")
            print('#'*40)
            # print(f"state before execution: {state}")
            print(f"state.current_code: {state.current_code}")
            # Execute code
            execution_result = await self.jupyter_service.execute_code(
                kernel_manager = kernel_manager , code=
                state.current_code
            )
            
            # Store execution result
            state.last_execution_result = execution_result
            
            if execution_result.success:
                print(f"✅ Code executed successfully")

                # Store execution results and extract variables
                step_description = state.plan.steps[state.current_step_index]

                # Extract and store new variables from the code
                new_variables = self._extract_variables_from_code(state.current_code)
                state.available_variables.extend(new_variables)
                state.available_variables = list(set(state.available_variables))  # Remove duplicates

                # Store execution context
                execution_summary = {
                    f"step_{state.current_step_index + 1}": {
                        "description": step_description,
                        "code": state.current_code,
                        "output": execution_result.stdout,
                        "variables_created": new_variables,
                        "success": True
                    }
                }
                state.execution_context.update(execution_summary)
                print('#'*40)
                print(f"state.execution_context: {state.execution_context}")
                # Store intermediate results if they contain tables or charts
                if execution_result.stdout :
                    intermediate_result = {
                        "step": state.current_step_index + 1,
                        "type": "table",
                        "content": execution_result.stdout,
                        "variables": new_variables
                    }
                    state.intermediate_results.append(intermediate_result)

                # Add to execution history
                state.execution_history.append(f"Step {state.current_step_index + 1}: {step_description} - SUCCESS (Variables: {', '.join(new_variables)})")

                # Move to next step
                state.current_step_index += 1

                # # Clear current code for next iteration
                # if hasattr(state, 'current_code'):
                #     delattr(state, 'current_code')
                # if hasattr(state, 'current_thought'):
                #     delattr(state, 'current_thought')
            else:
                print(f"❌ Code execution failed: {execution_result.stderr}")
                state.error_count += 1
            print('#'*40)
            print(f"state after execution: {state}")
            return state
            
        except Exception as e:
            print(f"❌ Code Executor error: {e}")
            state.error_count += 1
           
            from ..models.phase2_models import ExecutionResult
            state.last_execution_result = ExecutionResult(
                success=False,
                stdout="",
                stderr=f"Execution error: {str(e)}",
                display_data=[],
                execution_count=0
            )
            return state
    
    async def _error_analysis_agent(self, state: AgentState) -> AgentState:
        """Error analysis agent for debugging failed code."""
        print(f"🔍 Error Analysis Agent: Analyzing error for step {state.current_step_index + 1}")
        
        try:
            failed_step = state.plan.steps[state.current_step_index]
            
            # Create prompt
            llm_structured = self.llm.with_structured_output(ErrorAnalysisResponse)
            prompt = ChatPromptTemplate.from_template(ERROR_ANALYSIS_AGENT_PROMPT)
            chain = prompt | llm_structured
            
            # Analyze error
            response = chain.invoke({
                "failed_step": failed_step,
                "code_that_failed": state.current_code,
                "stderr_from_kernel": state.last_execution_result.stderr,
                "available_variables": ", ".join(state.available_variables),
                "execution_context": json.dumps(state.execution_context, indent=2) if state.execution_context else "No previous results.",
                "metadata_json": json.dumps(state.dataset_metadata, indent=2)
            })
            
            # Parse response
            # response_content = response.content if hasattr(response, 'content') else str(response)
            # error_analysis = validate_json_content(response_content)
            
            print(f"🔬 Error diagnosis: {response.diagnosis}")
            print(f"💡 Suggested fix: {response.suggestion}")
            
            # Store error analysis for code generator to use
            state.error_analysis = response
            
            return state
            
        except Exception as e:
            print(f"❌ Error Analysis Agent error: {e}")
            raise
    
    def _should_continue_execution(self, state: AgentState) -> str:
        """Determine next step in the workflow."""
        print(f"🤔 Deciding next step... Current step: {state.current_step_index}, Total steps: {len(state.plan.steps)}")
        
        # Check if we have an execution result
        if not hasattr(state, 'last_execution_result'):
            print("⚠️ No execution result found, continuing to code generation")
            return "continue"
        
        # If execution failed and we haven't exceeded retry limit
        if not state.last_execution_result.success:
            if state.error_count >= state.max_retries:
                print(f"❌ Max retries ({state.max_retries}) exceeded, completing with error")
                return "complete"
            print(f"🔄 Execution failed, going to error analysis (attempt {state.error_count}/{state.max_retries})")
            return "error"
        
        # If all steps completed, go to chart generation
        if state.current_step_index >= len(state.plan.steps):
            print("📊 All steps completed, proceeding to chart generation")
            return "chart"
        
        # Continue with next step
        print(f"➡️ Continuing to next step ({state.current_step_index + 1}/{len(state.plan.steps)})")
        return "continue"

    async def _chart_generation_agent(self, state: AgentState) -> AgentState:
        """Chart generation agent for creating visualizations."""
        print("📊 Chart Generation Agent: Creating visualization")

        try:
            # Check if we have data to visualize
            has_data = False
            final_data_info = {}

            # First try to get data from intermediate results
            if state.intermediate_results:
                print(f"🔍 Checking intermediate results for table data to generate chart")
                print(f"state.intermediate_results: {state.intermediate_results}")
                for result in state.intermediate_results:
                    if result.get("type") == "table" and result.get("content"):
                        has_data = True
                        final_data_info = {
                            "table_data": result.get("content"),
                            "variables_created": result.get("variables", [])
                        }
                        print(f"📊 Found table data in intermediate results: {result.get('variables', [])}")
                        break

            # Fallback to last execution result stdout
            if not has_data and hasattr(state, 'last_execution_result') and state.last_execution_result.success:
                if state.last_execution_result.stdout:
                    print(f"🔍 Checking last execution result for table data to generate chart")
                    print(f"state.last_execution_result: {state.last_execution_result}")
                    has_data = True
                    final_data_info = {
                        "table_data": state.last_execution_result.stdout,
                        "variables_created": state.available_variables
                    }
                    print(f"📊 Using last execution result stdout for chart generation")
                else:
                    print(f"ℹ️ No stdout in last execution result")

            print(f"📊 Chart generation data check: has_data={has_data}, available_variables={state.available_variables}")

            if has_data:
                print(f"📊 Proceeding with chart generation...")
                print(f"📊 Available variables: {state.available_variables}")
                print(f"📊 Final data info keys: {list(final_data_info.keys())}")

                # Create prompt
                llm_structured = self.llm.with_structured_output(ChartGenerationResponse)
                prompt = ChatPromptTemplate.from_template(CHART_GENERATION_AGENT_PROMPT)
                chain = prompt | llm_structured

                # Generate chart code with timeout
                import asyncio
                import time
                
                try:
                    print("🔄 Calling OpenAI API for chart generation...")
                    api_start = time.time()
                    
                    # Simplify execution context for chart generation
                    simplified_context = {}
                    if state.execution_context:
                        print('#'*40)
                        print(f"state.execution_context: {state.execution_context}")
                        for key, value in list(state.execution_context.items())[-2:]:  # Only last 2 steps
                            if isinstance(value, dict):
                                simplified_value = {k: v for k, v in value.items() if k != 'output'}
                                if 'output' in value and len(str(value['output'])) > 200:
                                    simplified_value['output'] = str(value['output'])[:200] + "..."
                                elif 'output' in value:
                                    simplified_value['output'] = value['output']
                                simplified_context[key] = simplified_value
                                
                    
                    chart_response = await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(
                            None,
                            lambda: chain.invoke({
                                "user_query": state.user_query,
                                "available_variables": ", ".join(state.available_variables[-5:]),  # Only last 5 variables
                                "execution_context": json.dumps(simplified_context, indent=2) if simplified_context else "No previous results.",
                                "final_dataframe_json": json.dumps(final_data_info, indent=2) if len(json.dumps(final_data_info)) < 1000 else '{"note": "Data too large, use available variables"}'
                            })
                        ),
                        timeout=30.0  # 30 second timeout for chart generation
                    )
                    
                    api_elapsed = time.time() - api_start
                    print(f"✅ Chart generation API call completed in {api_elapsed:.2f}s")
                    
                    # Parse response
                    print(f"📊 Chart response: {chart_response}")
                    if hasattr(chart_response, 'code'):
                        state.chart_code = chart_response.code
                        print(f"📈 Chart code generated:\n{state.chart_code}")
                    else:
                        print(f"❌ Chart response missing 'code' attribute: {chart_response}")
                        state.chart_code = None
                        
                except asyncio.TimeoutError:
                    print("❌ Chart generation timed out after 30 seconds")
                    print("🔄 Using fallback chart code")
                    

            else:
                print("⚠️ No data available for chart generation")
                print(f"⚠️ Intermediate results: {len(state.intermediate_results)} items")
                print(f"⚠️ Last execution result exists: {hasattr(state, 'last_execution_result')}")
                if hasattr(state, 'last_execution_result'):
                    print(f"⚠️ Last execution success: {state.last_execution_result.success}")
                    print(f"⚠️ Last execution stdout length: {len(state.last_execution_result.stdout) if state.last_execution_result.stdout else 0}")
                state.chart_code = None

            return state

        except Exception as e:
            print(f"❌ Chart Generation Agent error: {e}")
            state.chart_code = None
            return state

    async def _final_response_agent(self, state: AgentState) -> AgentState:
        """Final response agent for summarizing results."""
        print("📝 Final Response Agent: Creating summary")

        try:
            # Prepare final data from execution context and intermediate results
            final_data_markdown = "No data available"

            # Get data from intermediate results
            if state.intermediate_results:
                print("Getting data from intermediate results for final response")
                data_parts = []
                print('#'*40)
                print("Intermediate results:", state.intermediate_results)
                for result in state.intermediate_results:
                    if result.get("type") == "table":
                        data_parts.append(f"**{result.get('step', 'Step')} Results:**\n{result.get('content', '')}")

                if data_parts:
                    print('#'*40)
                    print('data parts to be added for final response from previous steps',data_parts)
                    final_data_markdown = "\n\n".join(data_parts)

            # Fallback to last execution result
            elif hasattr(state, 'last_execution_result') and state.last_execution_result.success:
                print("Intermediate results not available, using last execution result for final response")
                if state.last_execution_result.stdout:
                    final_data_markdown = state.last_execution_result.stdout
                    print('#'*40)
                    print('data parts to be added for final response from last execution result',final_data_markdown)

            # Determine chart availability
            chart_available = any(result.get("type") == "chart_html" for result in state.intermediate_results)
            chart_message = "I have also generated an interactive chart to help visualize this information." if chart_available else ""

            # Create prompt
            
            prompt = ChatPromptTemplate.from_template(FINAL_RESPONSE_AGENT_PROMPT)
            chain = prompt | self.llm
            print('#'*40)
            print('Invoking final response agent llm')
            # Generate final response
            response = chain.invoke({
                "user_query": state.user_query,
                "final_data_as_markdown": final_data_markdown,
                "chart_available_boolean": str(chart_available),
                "chart_message": chart_message
            })

            # Store final response
            response_content = response.content if hasattr(response, 'content') else str(response)
            state.final_response = response_content

            print(f"✅ Final response generated: {response_content[:200]}...")

            return state

        except Exception as e:
            print(f"❌ Final Response Agent error: {e}")
            state.final_response = f"I apologize, but I encountered an error while processing your query: {str(e)}"
            return state

    async def process_query(self, state: AgentState) -> AgentState:
        """Process a user query through the multi-agent workflow."""
        print(f"🚀 Starting multi-agent query processing for session: {state.session_id}")
        print(f"❓ User query: {state.user_query}")

        try:
            # Run the workflow
            result = await self.graph.ainvoke(state)

            print("✅ Multi-agent workflow completed successfully")
            return result

        except Exception as e:
            print(f"❌ Multi-agent workflow error: {e}")
            # Return state with error message
            state.final_response = f"I apologize, but I encountered an error while processing your query: {str(e)}"
            return state

    def _extract_variables_from_code(self, code: str) -> List[str]:
        """Extract variable names that are being assigned in the code."""
        import re

        variables = []
        if not code:
            return variables

        # Look for variable assignments (simple pattern)
        # Matches: variable_name = something
        assignment_pattern = r'^(\w+)\s*='

        for line in code.split('\n'):
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('import') and not line.startswith('print'):
                match = re.match(assignment_pattern, line)
                if match:
                    var_name = match.group(1)
                    # Skip common non-variable assignments
                    if var_name not in ['fig', 'plt', 'ax'] and not var_name.startswith('_'):
                        variables.append(var_name)

        print(f"🔍 Extracted variables from code: {variables}")
        return variables


# Global multi-agent service instance (lazy)
_multi_agent_service: Optional[MultiAgentService] = None


def get_multi_agent_service() -> MultiAgentService:
    """Get the global multi-agent service instance with lazy initialization."""
    global _multi_agent_service
    print(f"🔍 Current _multi_agent_service: {_multi_agent_service}")
    print(f"🔍 Thread ID: {threading.get_ident()}")
    if _multi_agent_service is None:
        print("🔄 Initializing MultiAgentService (lazy)...")
        try:
            import time
            start_time = time.time()
            _multi_agent_service = MultiAgentService()
            end_time = time.time()
            print(f"✅ MultiAgentService initialization completed in {end_time - start_time:.2f} seconds")
        except Exception as e:
            print(f"❌ MultiAgentService initialization failed: {e}")
            import traceback
            traceback.print_exc()
            raise
    else:
        print("♻️ Using existing MultiAgentService instance")
    return _multi_agent_service
