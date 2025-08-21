"""Session management service for Phase 2 with Jupyter kernel integration."""

import asyncio
import os
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
from jupyter_client import KernelManager

from ..config.settings import get_settings
from ..models.phase2_models import SessionInfo, ConversationTurn
from ..utils.file_utils import ensure_directory_exists, file_exists


class SessionManager:
    """Manages user sessions with Jupyter kernels and data persistence."""
    
    def __init__(self):
        """Initialize the session manager."""
        self.settings = get_settings()
        self.sessions: Dict[str, SessionInfo] = {}
        self.kernel_managers: Dict[str, KernelManager] = {}
        self.conversation_histories: Dict[str, List[Dict[str, Any]]] = {}
        self.kernel_initialized: Dict[str, bool] = {}  # Track kernel initialization status
        self.temp_data_dir = "temp_data"
        ensure_directory_exists(self.temp_data_dir)
        print(f"📁 SessionManager initialized with temp directory: {self.temp_data_dir}")
    
    async def create_session(self, dataset_name: str) -> str:
        """
        Create a new session with Jupyter kernel and data preparation.
        
        Args:
            dataset_name: Name of the dataset to load
            
        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())
        print(f"🆕 Creating new session: {session_id} for dataset: {dataset_name}")
        
        try:
            try:
                base_name = os.path.splitext(os.path.basename(dataset_name))[0]
                output_filename = f"{base_name}_filtered.parquet"
                parquet_path = os.path.join(self.temp_data_dir, output_filename)
                print(f"💾 Dataset detected as parquet: {parquet_path}")
            except Exception as e:
                print(f"❌ Failed to detect parquet file: {e}")
                raise
            
            # Start Jupyter kernel with timeout
            print(f"🚀 Starting Jupyter kernel for session: {session_id}")
            try:
                import time
                start_time = time.time()
                kernel_manager = KernelManager()
                kernel_manager.start_kernel()
                kernel_start_time = time.time() - start_time
                print(f"✅ Kernel started in {kernel_start_time:.2f}s")
                kernel_id = kernel_manager.kernel_id
                print(f"🔧 Kernel ID: {kernel_id}")
            except Exception as e:
                print(f"❌ Failed to start kernel: {e}")
                raise
            
            # Store kernel manager
            self.kernel_managers[session_id] = kernel_manager
            print(f"🔧 Kernel started with ID: {kernel_id}")
            
            # Initialize kernel with data loading (in background to avoid blocking)
            print(f"🔧 Starting background kernel initialization...")
            asyncio.create_task(self._initialize_kernel_background(session_id, parquet_path))
            
            # Create session info
            session_info = SessionInfo(
                session_id=session_id,
                dataset_name=dataset_name,
                created_at=datetime.now().isoformat(),
                last_activity=datetime.now().isoformat(),
                kernel_id=kernel_id,
                parquet_path=parquet_path
            )
            
            self.sessions[session_id] = session_info
            self.conversation_histories[session_id] = []
            self.kernel_initialized[session_id] = False  # Mark as not initialized yet
            print(f"✅ Session created successfully: {session_id}")

            return session_id
            
        except Exception as e:
            print(f"❌ Failed to create session {session_id}: {e}")
            # Cleanup on failure
            await self._cleanup_session(session_id)
            raise
    
    async def _initialize_kernel_background(self, session_id: str, parquet_path: str) -> None:
        """Initialize kernel in background without blocking session creation."""
        try:
            print(f"🔧 Background: Initializing kernel for session: {session_id}")
            await self._initialize_kernel(session_id, parquet_path)
            self.kernel_initialized[session_id] = True  # Mark as initialized
            print(f"✅ Background: Kernel initialization completed for session: {session_id}")
        except Exception as e:
            print(f"❌ Background: Kernel initialization failed for session {session_id}: {e}")
            # Don't raise - just log the error
    
    async def _initialize_kernel(self, session_id: str, parquet_path: str) -> None:
        """Initialize the Jupyter kernel with data loading code."""
        print(f"🔧 Initializing kernel for session: {session_id}")
        
        initialization_code = f"""
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Load the dataset from parquet file
print("Loading dataset from parquet file...")
df = pd.read_parquet(r'{parquet_path}')
print(f"Dataset loaded successfully: {{len(df)}} rows, {{len(df.columns)}} columns")
print("Available columns:", list(df.columns))

# Store dataset info for reference
dataset_info = {{
    'shape': df.shape,
    'columns': list(df.columns),
    'dtypes': dict(df.dtypes.astype(str)),
    'memory_usage': df.memory_usage(deep=True).sum()
}}

print("\\nDataset info:")
print(df.info())
print("\\nFirst few rows:")
print(df.head())
print("\\n✅ Dataset is ready for analysis as 'df' variable")
"""
        
        try:
            kernel_manager = self.kernel_managers[session_id]
            client = kernel_manager.client()
            
            # Execute initialization code
            msg_id = client.execute(initialization_code)
            
            # Wait for execution to complete
            timeout = 30  # 30 seconds timeout
            start_time = asyncio.get_event_loop().time()
            
            while True:
                try:
                    msg = client.get_iopub_msg(timeout=1)
                    if msg['parent_header'].get('msg_id') == msg_id:
                        if msg['msg_type'] == 'execute_result' or msg['msg_type'] == 'stream':
                            if 'text' in msg['content']:
                                print(f"📝 Kernel output: {msg['content']['text'].strip()}")
                        elif msg['msg_type'] == 'status' and msg['content']['execution_state'] == 'idle':
                            print(f"✅ Kernel initialized successfully for session: {session_id}")
                            break
                        elif msg['msg_type'] == 'error':
                            error_msg = '\n'.join(msg['content']['traceback'])
                            print(f"❌ Kernel initialization error: {error_msg}")
                            raise RuntimeError(f"Kernel initialization failed: {error_msg}")
                            
                except Exception as e:
                    if asyncio.get_event_loop().time() - start_time > timeout:
                        print(f"⏰ Kernel initialization timeout for session: {session_id}")
                        raise TimeoutError("Kernel initialization timed out")
                    continue
                    
        except Exception as e:
            print(f"❌ Failed to initialize kernel for session {session_id}: {e}")
            raise
    
    async def wait_for_kernel_initialization(self, session_id: str, timeout: float = 30.0) -> bool:
        """Wait for kernel initialization to complete."""
        if session_id not in self.kernel_initialized:
            return False
        
        start_time = asyncio.get_event_loop().time()
        while not self.kernel_initialized[session_id]:
            if asyncio.get_event_loop().time() - start_time > timeout:
                print(f"⏰ Kernel initialization timeout for session: {session_id}")
                return False
            await asyncio.sleep(0.5)  # Check every 500ms
        
        print(f"✅ Kernel ready for session: {session_id}")
        return True
    
    def is_kernel_initialized(self, session_id: str) -> bool:
        """Check if kernel is initialized for a session."""
        return self.kernel_initialized.get(session_id, False)
    
    async def get_session(self, session_id: str) -> Optional[SessionInfo]:
        """Get session information."""
        session = self.sessions.get(session_id)
        if session:
            # Update last activity
            session.last_activity = datetime.now().isoformat()
            print(f"📋 Retrieved session: {session_id}")
        else:
            print(f"❌ Session not found: {session_id}")
        return session
    
    def get_kernel_manager(self, session_id: str) -> Optional[KernelManager]:
        """Get kernel manager for a session."""
        kernel_manager = self.kernel_managers.get(session_id)
        if kernel_manager:
            print(f"🔧 Retrieved kernel manager for session: {session_id}")
        else:
            print(f"❌ Kernel manager not found for session: {session_id}")
        return kernel_manager
    
    async def cleanup_inactive_sessions(self, max_inactive_minutes: int = 30) -> None:
        """Clean up sessions that have been inactive for too long."""
        print(f"🧹 Starting cleanup of inactive sessions (max inactive: {max_inactive_minutes} minutes)")
        
        cutoff_time = datetime.now() - timedelta(minutes=max_inactive_minutes)
        sessions_to_cleanup = []
        
        for session_id, session_info in self.sessions.items():
            last_activity = datetime.fromisoformat(session_info.last_activity)
            if last_activity < cutoff_time:
                sessions_to_cleanup.append(session_id)
        
        for session_id in sessions_to_cleanup:
            print(f"🗑️ Cleaning up inactive session: {session_id}")
            await self._cleanup_session(session_id)
        
        if sessions_to_cleanup:
            print(f"✅ Cleaned up {len(sessions_to_cleanup)} inactive sessions")
        else:
            print("✅ No inactive sessions to clean up")
    
    async def _cleanup_session(self, session_id: str) -> None:
        """Clean up a specific session."""
        print(f"🗑️ Cleaning up session: {session_id}")
        
        try:
            # Stop kernel if exists
            if session_id in self.kernel_managers:
                kernel_manager = self.kernel_managers[session_id]
                if kernel_manager.is_alive():
                    kernel_manager.shutdown_kernel(now=True)
                del self.kernel_managers[session_id]
                print(f"🛑 Kernel stopped for session: {session_id}")
            
            # Remove parquet file if exists
            if session_id in self.sessions:
                session_info = self.sessions[session_id]
                if file_exists(session_info.parquet_path):
                    os.remove(session_info.parquet_path)
                    print(f"🗂️ Parquet file removed: {session_info.parquet_path}")
                del self.sessions[session_id]

            # Remove conversation history
            if session_id in self.conversation_histories:
                del self.conversation_histories[session_id]
                print(f"💬 Conversation history removed for session: {session_id}")
            
            print(f"✅ Session cleanup completed: {session_id}")
            
        except Exception as e:
            print(f"❌ Error during session cleanup {session_id}: {e}")
    
    async def shutdown_all_sessions(self) -> None:
        """Shutdown all active sessions."""
        print("🛑 Shutting down all sessions...")
        
        session_ids = list(self.sessions.keys())
        for session_id in session_ids:
            await self._cleanup_session(session_id)
        
        print(f"✅ All {len(session_ids)} sessions shut down")

    def add_conversation_turn(self, session_id: str, user_query: str, agent_response: str) -> None:
        """Add a conversation turn to the session history."""
        if session_id not in self.conversation_histories:
            self.conversation_histories[session_id] = []

        from datetime import datetime
        turn = {
            "user_query": user_query,
            "agent_response": agent_response,
            "timestamp": datetime.now().isoformat()
        }

        self.conversation_histories[session_id].append(turn)
        print(f"💬 Added conversation turn to session {session_id}")

    def get_conversation_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get conversation history for a session."""
        return self.conversation_histories.get(session_id, [])


# Global session manager instance (lazy)
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get the global session manager instance with lazy initialization."""
    global _session_manager
    if _session_manager is None:
        print("🔄 Initializing SessionManager (lazy)...")
        _session_manager = SessionManager()
    return _session_manager
