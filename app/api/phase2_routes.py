"""Phase 2 API routes for natural language querying with multi-agent system."""

import json
import os
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from ..models.phase2_models import QueryRequest, QueryResponse
from ..services.session_service import get_session_manager
from ..services.websocket_service import get_websocket_manager, get_streaming_service
from ..utils.file_utils import get_metadata_file_path, file_exists, load_json_file

router = APIRouter()


@router.post("/v2/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """
    Process a natural language query using the multi-agent system.
    
    Args:
        request: Query request with session info and user query
        
    Returns:
        Response with session ID and WebSocket URL for streaming
    """
    print(f"🔍 Processing query request for dataset: {request.dataset_name}")
    print(f"❓ User query: {request.query}")
    
    try:
        session_manager = get_session_manager()
        
        # Create or get session
        if request.session_id:
            print(f"📋 Using existing session: {request.session_id}")
            session_info = await session_manager.get_session(request.session_id)
            if not session_info:
                raise HTTPException(status_code=404, detail=f"Session not found: {request.session_id}")
            session_id = request.session_id
        else:
            print(f"🆕 Creating new session for dataset: {request.dataset_name}")
            session_id = await session_manager.create_session(request.dataset_name)
        
        # Load dataset metadata
        metadata_file_path = get_metadata_file_path(request.dataset_name)
        if not file_exists(metadata_file_path):
            raise HTTPException(
                status_code=404, 
                detail=f"Dataset metadata not found: {metadata_file_path}. Please run Phase 1 analysis first."
            )
        
        dataset_metadata = load_json_file(metadata_file_path)
        print(f"📊 Loaded metadata for dataset: {request.dataset_name}")
        
        # Prepare WebSocket URL
        websocket_url = f"ws://localhost:8000/v2/stream/{session_id}"
        
        print(f"✅ Query request processed successfully")
        print(f"🔗 WebSocket URL: {websocket_url}")
        
        return JSONResponse(content={
            "session_id": session_id,
            "websocket_url": websocket_url
        })
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Query processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process query: {str(e)}")


@router.websocket("/v2/stream/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time streaming of agent execution.
    
    Args:
        websocket: WebSocket connection
        session_id: Session identifier
    """
    print(f"🔌 WebSocket connection request for session: {session_id}")
    
    websocket_manager = get_websocket_manager()
    streaming_service = get_streaming_service()
    session_manager = get_session_manager()
    
    try:
        # Verify session exists
        session_info = await session_manager.get_session(session_id)
        if not session_info:
            print(f"❌ Session not found: {session_id}")
            await websocket.close(code=4004, reason="Session not found")
            return
        
        # Accept WebSocket connection
        await websocket_manager.connect(websocket, session_id)
        
        print(f"✅ WebSocket connected for session: {session_id}")
        
        # Wait for messages from client
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                print(f"📨 Raw message received: {data}")

                try:
                    message = json.loads(data)
                    print(f"📨 Parsed message from client: {message}")
                except json.JSONDecodeError as e:
                    print(f"❌ JSON parsing error: {e}")
                    await websocket_manager.send_error(session_id, f"Invalid JSON: {str(e)}")
                    continue
                
                # Check if it's a query message
                if message.get("type") == "query":
                    user_query = message.get("query")
                    # Use stored conversation history from session, fallback to provided history
                    stored_history = session_manager.get_conversation_history(session_id)
                    provided_history = message.get("conversation_history", [])
                    conversation_history = stored_history if stored_history else provided_history

                    if user_query:
                        print(f"🚀 Starting query processing: {user_query}")
                        print(f"💬 Using conversation history: {len(conversation_history)} previous turns")

                        # Load dataset metadata
                        metadata_file_path = get_metadata_file_path(session_info.dataset_name)
                        dataset_metadata = load_json_file(metadata_file_path)

                        # Process query with streaming
                        try:
                            await streaming_service.process_query_with_streaming(
                                session_id=session_id,
                                user_query=user_query,
                                dataset_metadata=dataset_metadata,
                                conversation_history=conversation_history
                            )
                        except Exception as e:
                            print(f"❌ Error processing query: {e}")
                            await websocket_manager.send_error(session_id, f"Query processing error: {str(e)}")
                    else:
                        await websocket_manager.send_error(session_id, "No query provided")
                
                elif message.get("type") == "ping":
                    # Handle ping messages
                    await websocket_manager.send_log(session_id, "pong")
                
                else:
                    await websocket_manager.send_error(session_id, f"Unknown message type: {message.get('type')}")
                    
            except WebSocketDisconnect:
                print(f"🔌 WebSocket disconnected for session: {session_id}")
                break
            except Exception as e:
                print(f"❌ WebSocket message processing error: {e}")
                await websocket_manager.send_error(session_id, f"Message processing error: {str(e)}")
                
    except WebSocketDisconnect:
        print(f"🔌 WebSocket disconnected during setup for session: {session_id}")
    except Exception as e:
        print(f"❌ WebSocket connection error for session {session_id}: {e}")
        try:
            await websocket.close(code=4000, reason=f"Connection error: {str(e)}")
        except:
            pass
    finally:
        # Clean up connection
        websocket_manager.disconnect(session_id)
        print(f"🧹 WebSocket cleanup completed for session: {session_id}")


@router.get("/v2/sessions")
async def get_active_sessions():
    """Get information about active sessions."""
    print("📋 Retrieving active sessions information")
    
    try:
        session_manager = get_session_manager()
        websocket_manager = get_websocket_manager()
        
        active_sessions = list(session_manager.sessions.keys())
        websocket_connections = websocket_manager.get_active_sessions()
        
        return JSONResponse(content={
            "active_sessions": len(active_sessions),
            "websocket_connections": len(websocket_connections),
            "sessions": [
                {
                    "session_id": session_id,
                    "dataset_name": session_info.dataset_name,
                    "created_at": session_info.created_at,
                    "last_activity": session_info.last_activity,
                    "has_websocket": session_id in websocket_connections
                }
                for session_id, session_info in session_manager.sessions.items()
            ]
        })
        
    except Exception as e:
        print(f"❌ Error retrieving sessions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve sessions: {str(e)}")


@router.delete("/v2/sessions/{session_id}")
async def cleanup_session(session_id: str):
    """Manually cleanup a specific session."""
    print(f"🗑️ Manual cleanup request for session: {session_id}")
    
    try:
        session_manager = get_session_manager()
        websocket_manager = get_websocket_manager()
        
        # Check if session exists
        if session_id not in session_manager.sessions:
            raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
        
        # Disconnect WebSocket if active
        if session_id in websocket_manager.active_connections:
            websocket_manager.disconnect(session_id)
        
        # Cleanup session
        await session_manager._cleanup_session(session_id)
        
        print(f"✅ Session cleanup completed: {session_id}")
        
        return JSONResponse(content={
            "status": "success",
            "message": f"Session {session_id} cleaned up successfully"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Session cleanup error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cleanup session: {str(e)}")


@router.post("/v2/sessions/cleanup")
async def cleanup_inactive_sessions(max_inactive_minutes: int = 30):
    """Cleanup all inactive sessions."""
    print(f"🧹 Cleanup request for inactive sessions (max inactive: {max_inactive_minutes} minutes)")
    
    try:
        session_manager = get_session_manager()
        
        # Get count before cleanup
        sessions_before = len(session_manager.sessions)
        
        # Cleanup inactive sessions
        await session_manager.cleanup_inactive_sessions(max_inactive_minutes)
        
        # Get count after cleanup
        sessions_after = len(session_manager.sessions)
        cleaned_up = sessions_before - sessions_after
        
        print(f"✅ Cleanup completed: {cleaned_up} sessions cleaned up")
        
        return JSONResponse(content={
            "status": "success",
            "message": f"Cleaned up {cleaned_up} inactive sessions",
            "sessions_before": sessions_before,
            "sessions_after": sessions_after,
            "cleaned_up": cleaned_up
        })
        
    except Exception as e:
        print(f"❌ Cleanup error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cleanup sessions: {str(e)}")