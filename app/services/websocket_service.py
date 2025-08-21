"""WebSocket streaming service for real-time agent communication."""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import WebSocket, WebSocketDisconnect

from ..models.phase2_models import MessageType, StreamMessage

# Add conditional imports to avoid circular imports
try:
    from ..models.phase2_models import AgentState, ConversationTurn
    IMPORTS_AVAILABLE = True
    print("🔄 WebSocket service: Multi-agent imports successful")
except Exception as e:
    print(f"❌ WebSocket service: Import error: {e}")
    IMPORTS_AVAILABLE = False

# Defer multi_agent_service import to avoid circular imports
_multi_agent_service = None
_service_init_lock = asyncio.Lock()


class WebSocketManager:
    """Manages WebSocket connections for real-time streaming."""
    
    def __init__(self):
        """Initialize the WebSocket manager."""
        self.active_connections: Dict[str, WebSocket] = {}
        print("🔌 WebSocketManager initialized")
    
    async def connect(self, websocket: WebSocket, session_id: str) -> None:
        """Accept a WebSocket connection and store it."""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        print(f"🔗 WebSocket connected for session: {session_id}")
        
        # Send welcome message
        await self.send_message(session_id, MessageType.LOG, "WebSocket connection established")
    
    def disconnect(self, session_id: str) -> None:
        """Remove a WebSocket connection."""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            print(f"🔌 WebSocket disconnected for session: {session_id}")
    
    async def send_message(
        self, 
        session_id: str, 
        message_type: MessageType, 
        payload: any,
        step_index: Optional[int] = None
    ) -> None:
        """Send a message to a specific session."""
        if session_id not in self.active_connections:
            print(f"⚠️ No WebSocket connection found for session: {session_id}")
            return
        
        try:
            message = StreamMessage(
                type=message_type,
                payload=payload,
                timestamp=datetime.now().isoformat(),
                step_index=step_index
            )

            websocket = self.active_connections[session_id]

            # Pre-check websocket state if available (Starlette)
            try:
                from starlette.websockets import WebSocketState
                ws_state = getattr(websocket, "client_state", None)
                if ws_state is not None and ws_state != WebSocketState.CONNECTED:
                    print(f"⚠️ WebSocket for session {session_id} not connected (state={ws_state}). Skipping send.")
                    self.disconnect(session_id)
                    return
            except Exception:
                # If state enum not available, continue best-effort
                pass

            # Avoid indefinite await hangs: send with timeout and rich error logs
            try:
                await asyncio.wait_for(
                    websocket.send_text(message.model_dump_json()),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                print(f"⏱️ send_text timeout for session {session_id} while sending {message_type.value}")
                return

            print(f"📤 Sent {message_type.value} message to session {session_id}: {str(payload)[:100]}...")

        except Exception as e:
            print(f"❌ Error sending message to session {session_id}: {e}")
            # Remove broken connection
            self.disconnect(session_id)
    
    async def send_thought(self, session_id: str, thought: str, step_index: Optional[int] = None) -> None:
        """Send an agent thought message."""
        await self.send_message(session_id, MessageType.THOUGHT, thought, step_index)
    
    async def send_code(self, session_id: str, code: str, step_index: Optional[int] = None) -> None:
        """Send generated code message."""
        await self.send_message(session_id, MessageType.CODE, code, step_index)
    
    async def send_log(self, session_id: str, log_message: str, step_index: Optional[int] = None) -> None:
        """Send a log message."""
        await self.send_message(session_id, MessageType.LOG, log_message, step_index)
    
    async def send_error(self, session_id: str, error_message: str, step_index: Optional[int] = None) -> None:
        """Send an error message."""
        await self.send_message(session_id, MessageType.ERROR, error_message, step_index)
    
    async def send_execution_start(self, session_id: str, step_index: int) -> None:
        """Send execution start notification."""
        await self.send_message(
            session_id, 
            MessageType.EXECUTION_START, 
            f"Starting execution of step {step_index + 1}",
            step_index
        )
    
    async def send_execution_success(self, session_id: str, output: str, step_index: int) -> None:
        """Send execution success notification."""
        await self.send_message(
            session_id, 
            MessageType.EXECUTION_SUCCESS, 
            output,
            step_index
        )
    
    async def send_execution_error(self, session_id: str, error: str, step_index: int) -> None:
        """Send execution error notification."""
        await self.send_message(
            session_id, 
            MessageType.EXECUTION_ERROR, 
            error,
            step_index
        )
    
    async def send_table(self, session_id: str, table_data: str, step_index: Optional[int] = None) -> None:
        """Send table data."""
        await self.send_message(session_id, MessageType.TABLE, table_data, step_index)
    
    async def send_chart(self, session_id: str, chart_data: dict, step_index: Optional[int] = None) -> None:
        """Send chart data."""
        await self.send_message(session_id, MessageType.CHART, chart_data, step_index)
    
    async def send_plan(self, session_id: str, plan: List[str]) -> None:
        """Send the execution plan."""
        await self.send_message(session_id, MessageType.PLAN, plan)
    
    async def send_final_response(self, session_id: str, response: str) -> None:
        """Send the final response."""
        await self.send_message(session_id, MessageType.FINAL_RESPONSE, response)
    
    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.active_connections)
    
    def get_active_sessions(self) -> List[str]:
        """Get list of active session IDs."""
        return list(self.active_connections.keys())


class StreamingMultiAgentService:
    """Multi-agent service with WebSocket streaming capabilities."""

    def __init__(self, websocket_manager: WebSocketManager):
        """Initialize with WebSocket manager."""
        self.websocket_manager = websocket_manager
        print("📡 StreamingMultiAgentService initialized")

    async def process_query_with_streaming(
        self,
        session_id: str,
        user_query: str,
        dataset_metadata: dict,
        conversation_history: List = None
    ) -> None:
        """Process a query with real-time streaming of the agent workflow."""
        print(f"🚀 Starting streaming query processing for session: {session_id}")
        print(f"❓ Query: {user_query}")
        print(f"📊 Dataset metadata keys: {list(dataset_metadata.keys()) if dataset_metadata else 'None'}")
        print(f"🔍 WebSocket manager exists: {self.websocket_manager is not None}")
        print(f"📍 Entering try block...")

        try:
            print(f"📍 Inside try block")
            # Check if OpenAI API key is available
            import os
            print(f"📍 Imported os module")
            api_key = os.getenv("OPENAI_API_KEY")
            print(f"📍 API key exists: {bool(api_key)}, length: {len(api_key) if api_key else 0}")
            if not api_key:
                error_msg = "OpenAI API key not found. Please set OPENAI_API_KEY in your .env file."
                print(f"❌ {error_msg}")
                await self.websocket_manager.send_error(session_id, error_msg)
                return

            print(f"📍 Imports already available, no need to import again")

            # Send initial log
            print(f"📍 About to send initial log message...")
            await self.websocket_manager.send_log(session_id, f"Processing query: {user_query}")
            print(f"📤 Sent initial log message")

            # Create agent state
            state = AgentState(
                session_id=session_id,
                user_query=user_query,
                dataset_metadata=dataset_metadata,
                conversation_history=[
                    ConversationTurn(**turn) for turn in (conversation_history or [])
                ]
            )

            # Wait for kernel initialization
            print(f"📊 Waiting for kernel initialization for session: {session_id}")
            await self.websocket_manager.send_log(session_id, "⚙️ Preparing analysis environment...")
            
            from ..services.session_service import get_session_manager
            session_manager = get_session_manager()
            kernel_ready = await session_manager.wait_for_kernel_initialization(session_id, timeout=30.0)
            
            if kernel_ready:
                await self.websocket_manager.send_log(session_id, "✅ Analysis environment ready!")
                print(f"✅ Kernel ready for session: {session_id}")
            else:
                await self.websocket_manager.send_error(session_id, "Kernel initialization timed out. Please try again.")
                print(f"❌ Kernel initialization timeout for session: {session_id}")
                return

            # Get multi-agent service - initialize once and reuse with proper locking
            print(f"🤖 Getting multi-agent service...")
            global _multi_agent_service
            
            try:
                # Use async lock to prevent concurrent initialization
                async with _service_init_lock:
                    if _multi_agent_service is None:
                        print(f"🔄 Multi-agent service not pre-initialized, initializing now...")
                        await self.websocket_manager.send_log(session_id, "⚙️ Initializing analysis engine (first time may take longer)...")
                        
                        def init_service():
                            print(f"🔄 Inside init_service thread...")
                            from ..services.multi_agent_service import get_multi_agent_service
                            print(f"🔄 Imported get_multi_agent_service")
                            service = get_multi_agent_service()
                            print(f"🔄 Service obtained from get_multi_agent_service")
                            return service
                        
                        loop = asyncio.get_event_loop()
                        print(f"🔄 Running service initialization...")
                        _multi_agent_service = await asyncio.wait_for(
                            loop.run_in_executor(None, init_service),
                            timeout=60.0  # Increased timeout for runtime initialization
                        )
                        
                        print(f"✅ Multi-agent service initialized successfully")
                        await self.websocket_manager.send_log(session_id, "✅ Analysis engine initialized successfully!")
                    else:
                        print(f"♻️ Using pre-initialized multi-agent service")
                
                multi_agent_service = _multi_agent_service
                print(f"✅ Multi-agent service obtained")
            except asyncio.TimeoutError:
                print(f"❌ Multi-agent service initialization timed out after 60 seconds")
                await self.websocket_manager.send_error(session_id, "Service initialization timed out. Please restart the server or try again.")
                return
            except Exception as e:
                print(f"❌ Failed to get multi-agent service: {e}")
                import traceback
                traceback.print_exc()
                await self.websocket_manager.send_error(session_id, f"Service initialization failed: {str(e)}")
                return

            # Process with streaming updates
            print(f"🔄 Starting streaming workflow...")
            try:
                await self._process_with_streaming(multi_agent_service, state)
                print(f"✅ Streaming workflow completed")
            except Exception as e:
                print(f"❌ Streaming workflow error: {e}")
                import traceback
                traceback.print_exc()
                await self.websocket_manager.send_error(session_id, f"Workflow error: {str(e)}")

        except Exception as e:
            print(f"❌ Streaming query processing error: {e}")
            await self.websocket_manager.send_error(session_id, f"Processing error: {str(e)}")

    async def _process_with_streaming(self, multi_agent_service, state) -> None:
        """Process the multi-agent workflow with streaming updates."""
        print(f"🔄 Entering _process_with_streaming method...")
        session_id = state.session_id
        print(f"📋 Session ID: {session_id}")

        try:
            print(f"🤖 Using provided multi-agent service...")
            await self.websocket_manager.send_log(session_id, "⚙️ Initializing analysis engine...")
            print(f"📤 Sent initialization message")

            # Step 1: Planning
            await self.websocket_manager.send_log(session_id, "🎯 Starting planning phase...")
            state = await multi_agent_service._planner_agent(state)

            if state.plan:
                await self.websocket_manager.send_plan(session_id, state.plan.steps)
                await self.websocket_manager.send_log(session_id, f"📋 Plan created with {len(state.plan.steps)} steps")

            # Step 2: Execute plan steps
            while state.current_step_index < len(state.plan.steps):
                step_index = state.current_step_index
                current_step = state.plan.steps[step_index]

                await self.websocket_manager.send_log(
                    session_id,
                    f"📝 Step {step_index + 1}/{len(state.plan.steps)}: {current_step}",
                    step_index
                )

                # Code generation with timeout
                await self.websocket_manager.send_log(session_id, "💻 Generating code...", step_index)
                try:
                    state = await asyncio.wait_for(
                        multi_agent_service._code_generation_agent(state),
                        timeout=50.0  # 50 second timeout at service level
                    )
                except asyncio.TimeoutError:
                    print(f"❌ Code generation timed out for step {step_index + 1}")
                    await self.websocket_manager.send_error(
                        session_id,
                        f"Code generation timed out for step {step_index + 1}. Please try again with a simpler query.",
                        step_index
                    )
                    break  # Exit the loop

                if hasattr(state, 'current_thought'):
                    print("trying to send thought")
                    await self.websocket_manager.send_thought(session_id, state.current_thought, step_index)

                if hasattr(state, 'current_code'):
                    print("trying to send code")
                    await self.websocket_manager.send_code(session_id, state.current_code, step_index)

                # Code execution
                await self.websocket_manager.send_execution_start(session_id, step_index)
                state = await multi_agent_service._code_executor(state)

                if hasattr(state, 'last_execution_result'):
                    if state.last_execution_result.success:
                        await self.websocket_manager.send_execution_success(
                            session_id,
                            state.last_execution_result.stdout,
                            step_index
                        )

                        # Send table data if available
                        if state.last_execution_result.stdout:
                            await self.websocket_manager.send_table(
                                session_id,
                                state.last_execution_result.stdout,
                                step_index
                            )
                    else:
                        await self.websocket_manager.send_execution_error(
                            session_id,
                            state.last_execution_result.stderr,
                            step_index
                        )

                        # Error analysis if needed
                        if state.error_count < state.max_retries:
                            await self.websocket_manager.send_log(session_id, "🔍 Analyzing error...", step_index)
                            state = await multi_agent_service._error_analysis_agent(state)

                            if hasattr(state, 'error_analysis'):
                                await self.websocket_manager.send_log(
                                    session_id,
                                    f"💡 Error analysis: {state.error_analysis.suggestion}",
                                    step_index
                                )
                        else:
                            await self.websocket_manager.send_error(
                                session_id,
                                f"Max retries exceeded for step {step_index + 1}",
                                step_index
                            )
                            break

            # Step 3: Chart generation (if requested)
            chart_keywords = ["chart", "plot", "graph", "visualiz", "bar", "line", "pie", "scatter", "histogram"]
            needs_chart = any(keyword in state.user_query.lower() for keyword in chart_keywords)

            if needs_chart:
                await self.websocket_manager.send_log(session_id, "📊 Generating visualization...")
                try:
                    state = await asyncio.wait_for(
                        multi_agent_service._chart_generation_agent(state),
                        timeout=35.0  # 35 second timeout for chart generation
                    )
                except asyncio.TimeoutError:
                    print("❌ Chart generation timed out")
                    await self.websocket_manager.send_error(session_id, "Chart generation timed out. The analysis is complete but visualization could not be generated.")
                    state.chart_code = None
            else:
                await self.websocket_manager.send_log(session_id, "📊 No visualization requested, skipping chart generation...")
                state.chart_code = None

            if state.chart_code:
                await self.websocket_manager.send_code(session_id, state.chart_code)

                # Execute chart code to generate HTML
                await self.websocket_manager.send_log(session_id, "🎨 Executing chart generation...")

                # Get kernel manager and execute chart code
                from ..services.jupyter_service import get_jupyter_service
                from ..services.session_service import get_session_manager
                jupyter_service = get_jupyter_service()
                session_manager = get_session_manager()
                kernel_manager = session_manager.get_kernel_manager(session_id)
                if kernel_manager:
                    execution_result = await jupyter_service.execute_code(kernel_manager, state.chart_code)

                    if execution_result.success:
                        # Extract HTML from execution result
                        chart_html = execution_result.stdout if execution_result.stdout else None

                        if chart_html and len(chart_html.strip()) > 100:  # Basic validation
                            # Store chart HTML to file
                            from ..services.file_storage_service import get_file_storage_service
                            file_storage = get_file_storage_service()
                            file_info = file_storage.store_chart_html(session_id, chart_html, "chart")

                            # Store chart HTML in intermediate results
                            chart_result = {
                                "step": "chart_generation",
                                "type": "chart_html",
                                "content": chart_html,
                                "code": state.chart_code,
                                "file_info": file_info,
                                "variables": ["chart_html"]
                            }
                            state.intermediate_results.append(chart_result)

                            # Send chart to frontend
                            await self.websocket_manager.send_chart(session_id, {
                                "type": "html",
                                "content": chart_html,
                                "file_url": file_info.get("url", ""),
                                "filename": file_info.get("filename", "")
                            })
                            await self.websocket_manager.send_log(session_id, f"✅ Chart generated and saved as {file_info.get('filename', 'chart.html')}!")
                        else:
                            await self.websocket_manager.send_log(session_id, "⚠️ Chart code executed but no valid HTML output received")
                    else:
                        await self.websocket_manager.send_log(session_id, f"❌ Chart execution failed: {execution_result.stderr}")
                else:
                    await self.websocket_manager.send_log(session_id, "❌ No kernel manager available for chart execution")

            # Step 4: Final response
            await self.websocket_manager.send_log(session_id, "📝 Generating final response...")
            state = await multi_agent_service._final_response_agent(state)

            if state.final_response:
                await self.websocket_manager.send_final_response(session_id, state.final_response)

                # Save conversation turn to session history
                from ..services.session_service import get_session_manager
                session_manager = get_session_manager()
                session_manager.add_conversation_turn(session_id, state.user_query, state.final_response)

            await self.websocket_manager.send_log(session_id, "✅ Query processing completed!")

        except Exception as e:
            print(f"❌ Streaming processing error: {e}")
            await self.websocket_manager.send_error(session_id, f"Processing error: {str(e)}")


# class StreamingMultiAgentService:
#     """Multi-agent service with WebSocket streaming capabilities."""
    
#     def __init__(self, websocket_manager: WebSocketManager):
#         """Initialize with WebSocket manager."""
#         self.websocket_manager = websocket_manager
#         print("📡 StreamingMultiAgentService initialized")
    
#     async def process_query_with_streaming(
#         self,
#         session_id: str,
#         user_query: str,
#         dataset_metadata: dict,
#         conversation_history: List = None
#     ) -> None:
#         """Process a query with real-time streaming of the agent workflow."""
#         print(f"🚀 Starting streaming query processing for session: {session_id}")
#         print(f"❓ Query: {user_query}")
#         print(f"📊 Dataset metadata keys: {list(dataset_metadata.keys()) if dataset_metadata else 'None'}")

#         try:
#             # Check if OpenAI API key is available
#             import os
#             if not os.getenv("OPENAI_API_KEY"):
#                 error_msg = "OpenAI API key not found. Please set OPENAI_API_KEY in your .env file."
#                 print(f"❌ {error_msg}")
#                 await self.websocket_manager.send_error(session_id, error_msg)
#                 return

#             # Import here to avoid circular imports
#             from ..services.multi_agent_service import get_multi_agent_service
#             from ..models.phase2_models import AgentState, ConversationTurn

#             # Send initial log
#             await self.websocket_manager.send_log(session_id, f"Processing query: {user_query}")
#             print(f"📤 Sent initial log message")
            
#             # Create agent state
#             state = AgentState(
#                 session_id=session_id,
#                 user_query=user_query,
#                 dataset_metadata=dataset_metadata,
#                 conversation_history=[
#                     ConversationTurn(**turn) for turn in (conversation_history or [])
#                 ]
#             )

#             # Add context about pre-loaded data
#             await self.websocket_manager.send_log(session_id, "📊 Dataset is already loaded as 'df' variable in Jupyter kernel")
            
#             # Get multi-agent service
#             print(f"🤖 Getting multi-agent service...")
#             multi_agent_service = get_multi_agent_service()
#             print(f"✅ Multi-agent service obtained")

#             # Process with streaming updates
#             print(f"🔄 Starting streaming workflow...")
#             await self._process_with_streaming(multi_agent_service, state)
#             print(f"✅ Streaming workflow completed")
            
#         except Exception as e:
#             print(f"❌ Streaming query processing error: {e}")
#             await self.websocket_manager.send_error(session_id, f"Processing error: {str(e)}")
    
#     async def _process_with_streaming(self, multi_agent_service, state) -> None:
#         """Process the multi-agent workflow with streaming updates."""
#         print(f"🔄 Entering _process_with_streaming method...")
#         session_id = state.session_id
#         print(f"📋 Session ID: {session_id}")

#         try:
#             print(f"🤖 Using provided multi-agent service...")
#             await self.websocket_manager.send_log(session_id, "⚙️ Initializing analysis engine...")
#             print(f"📤 Sent initialization message")
#             # Step 1: Planning
#             await self.websocket_manager.send_log(session_id, "🎯 Starting planning phase...")
#             state = await multi_agent_service._planner_agent(state)
#             # print('#'*40)
#             # print("received state and printing state")
#             # print(state)
#             # print(state.plan)
#             if state.plan:
#                 await self.websocket_manager.send_plan(session_id, state.plan.steps)
#                 await self.websocket_manager.send_log(session_id, f"📋 Plan created with {len(state.plan.steps)} steps")
            
#             # Step 2: Execute plan steps
#             while state.current_step_index < len(state.plan.steps):
#                 step_index = state.current_step_index
#                 current_step = state.plan.steps[step_index]
                
#                 await self.websocket_manager.send_log(
#                     session_id, 
#                     f"📝 Step {step_index + 1}/{len(state.plan.steps)}: {current_step}",
#                     step_index
#                 )
                
#                 # Code generation
#                 await self.websocket_manager.send_log(session_id, "💻 Generating code...", step_index)
#                 # print(f"state before code generation: {state}")
#                 state = await multi_agent_service._code_generation_agent(state)
                
#                 if hasattr(state, 'current_thought'):
#                     print("trying to send thought")
#                     await self.websocket_manager.send_thought(session_id, state.current_thought, step_index)
                
#                 if hasattr(state, 'current_code'):
#                     print("trying to send code")
#                     await self.websocket_manager.send_code(session_id, state.current_code, step_index)
                
#                 # Code execution
#                 await self.websocket_manager.send_execution_start(session_id, step_index)
#                 state = await multi_agent_service._code_executor(state)
                
#                 if hasattr(state, 'last_execution_result'):
#                     if state.last_execution_result.success:
#                         await self.websocket_manager.send_execution_success(
#                             session_id, 
#                             state.last_execution_result.stdout,
#                             step_index
#                         )
                        
#                         # Send table data if available
#                         if state.last_execution_result.stdout:
#                             await self.websocket_manager.send_table(
#                                 session_id,
#                                 state.last_execution_result.stdout,
#                                 step_index
#                             )
#                     else:
#                         await self.websocket_manager.send_execution_error(
#                             session_id,
#                             state.last_execution_result.stderr,
#                             step_index
#                         )
                        
#                         # Error analysis if needed
#                         if state.error_count < state.max_retries:
#                             await self.websocket_manager.send_log(session_id, "🔍 Analyzing error...", step_index)
#                             state = await multi_agent_service._error_analysis_agent(state)
                            
#                             if hasattr(state, 'error_analysis'):
#                                 await self.websocket_manager.send_log(
#                                     session_id,
#                                     f"💡 Error analysis: {state.error_analysis.suggestion}",
#                                     step_index
#                                 )
#                         else:
#                             await self.websocket_manager.send_error(
#                                 session_id,
#                                 f"Max retries exceeded for step {step_index + 1}",
#                                 step_index
#                             )
#                             break
            
#             # Step 3: Chart generation (if requested)
#             chart_keywords = ["chart", "plot", "graph", "visualiz", "bar", "line", "pie", "scatter", "histogram"]
#             needs_chart = any(keyword in state.user_query.lower() for keyword in chart_keywords)

#             if needs_chart:
#                 await self.websocket_manager.send_log(session_id, "📊 Generating visualization...")
#                 state = await multi_agent_service._chart_generation_agent(state)
#             else:
#                 await self.websocket_manager.send_log(session_id, "📊 No visualization requested, skipping chart generation...")
#                 state.chart_code = None
            
#             if state.chart_code:
#                 await self.websocket_manager.send_code(session_id, state.chart_code)

#                 # Execute chart code to generate HTML
#                 await self.websocket_manager.send_log(session_id, "🎨 Executing chart generation...")
    
#                 # Get kernel manager and execute chart code
#                 from ..services.jupyter_service import get_jupyter_service
#                 from ..services.session_service import get_session_manager
#                 jupyter_service = get_jupyter_service()
#                 session_manager = get_session_manager()
#                 kernel_manager = session_manager.get_kernel_manager(session_id)
#                 if kernel_manager:
#                     execution_result = await jupyter_service.execute_code(kernel_manager, state.chart_code)

#                     if execution_result.success:
#                         # Extract HTML from execution result
#                         chart_html = execution_result.stdout if execution_result.stdout else None

#                         if chart_html and len(chart_html.strip()) > 100:  # Basic validation
#                             # Store chart HTML to file
#                             from ..services.file_storage_service import get_file_storage_service
#                             file_storage = get_file_storage_service()
#                             file_info = file_storage.store_chart_html(session_id, chart_html, "chart")

#                             # Store chart HTML in intermediate results
#                             chart_result = {
#                                 "step": "chart_generation",
#                                 "type": "chart_html",
#                                 "content": chart_html,
#                                 "code": state.chart_code,
#                                 "file_info": file_info,
#                                 "variables": ["chart_html"]
#                             }
#                             state.intermediate_results.append(chart_result)

#                             # Send chart to frontend
#                             await self.websocket_manager.send_chart(session_id, {
#                                 "type": "html",
#                                 "content": chart_html,
#                                 "file_url": file_info.get("url", ""),
#                                 "filename": file_info.get("filename", "")
#                             })
#                             await self.websocket_manager.send_log(session_id, f"✅ Chart generated and saved as {file_info.get('filename', 'chart.html')}!")
#                         else:
#                             await self.websocket_manager.send_log(session_id, "⚠️ Chart code executed but no valid HTML output received")
#                     else:
#                         await self.websocket_manager.send_log(session_id, f"❌ Chart execution failed: {execution_result.stderr}")
#                 else:
#                     await self.websocket_manager.send_log(session_id, "❌ No kernel manager available for chart execution")
            
#             # Step 4: Final response
#             await self.websocket_manager.send_log(session_id, "📝 Generating final response...")
#             state = await multi_agent_service._final_response_agent(state)

#             if state.final_response:
#                 await self.websocket_manager.send_final_response(session_id, state.final_response)

#                 # Save conversation turn to session history
#                 from ..services.session_service import get_session_manager
#                 session_manager = get_session_manager()
#                 session_manager.add_conversation_turn(session_id, state.user_query, state.final_response)

#             await self.websocket_manager.send_log(session_id, "✅ Query processing completed!")
            
#         except Exception as e:
#             print(f"❌ Streaming processing error: {e}")
#             await self.websocket_manager.send_error(session_id, f"Processing error: {str(e)}")


# Global WebSocket manager instance
websocket_manager = WebSocketManager()


def get_websocket_manager() -> WebSocketManager:
    """Get the global WebSocket manager instance."""
    return websocket_manager


def get_streaming_service() -> StreamingMultiAgentService:
    """Get the streaming multi-agent service instance."""
    return StreamingMultiAgentService(websocket_manager)
