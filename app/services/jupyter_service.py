"""Jupyter sandbox execution service for safe code execution."""

import asyncio
import json
from typing import Any, Dict, List, Optional

from jupyter_client import KernelManager

from ..models.phase2_models import ExecutionResult


class JupyterExecutionService:
    """Service for executing Python code in Jupyter kernels safely."""
    
    def __init__(self):
        """Initialize the execution service."""
        print("🔧 JupyterExecutionService initialized")
    
    async def execute_code(
        self, 
        kernel_manager: KernelManager, 
        code: str, 
        timeout: int = 60
    ) -> ExecutionResult:
        """
        Execute Python code in a Jupyter kernel and return results.
        
        Args:
            kernel_manager: The kernel manager for the session
            code: Python code to execute
            timeout: Execution timeout in seconds
            
        Returns:
            ExecutionResult with stdout, stderr, and display data
        """
        print(f"🚀 Executing code in kernel (timeout: {timeout}s)")
        print(f"📝 Code to execute:\n{code}")
        
        try:
            client = kernel_manager.client()
            
            # Execute the code
            msg_id = client.execute(code)
            print(f"📤 Code execution started with message ID: {msg_id}")
            
            # Collect results
            stdout_lines = []
            stderr_lines = []
            display_data = []
            execution_count = 0
            success = True
            
            start_time = asyncio.get_event_loop().time()
            
            while True:
                try:
                    # Get message from kernel
                    msg = client.get_iopub_msg(timeout=1)
                    
                    # Only process messages from our execution
                    if msg['parent_header'].get('msg_id') != msg_id:
                        continue
                    
                    msg_type = msg['msg_type']
                    content = msg['content']
                    
                    print(f"📨 Received message type: {msg_type}")
                    
                    if msg_type == 'stream':
                        # Handle stdout/stderr
                        stream_name = content.get('name', 'stdout')
                        text = content.get('text', '')
                        
                        if stream_name == 'stdout':
                            stdout_lines.append(text)
                            print(f"📤 STDOUT: {text.strip()}")
                        elif stream_name == 'stderr':
                            stderr_lines.append(text)
                            print(f"⚠️ STDERR: {text.strip()}")
                    
                    elif msg_type == 'execute_result':
                        # Handle execution results
                        execution_count = content.get('execution_count', 0)
                        data = content.get('data', {})
                        
                        # Capture text output
                        if 'text/plain' in data:
                            stdout_lines.append(data['text/plain'])
                            print(f"📊 Result: {data['text/plain'].strip()}")
                        
                        # Capture rich display data
                        if data:
                            display_data.append(data)
                            print(f"🎨 Display data captured: {list(data.keys())}")
                    
                    elif msg_type == 'display_data':
                        # Handle display data (plots, tables, etc.)
                        data = content.get('data', {})
                        if data:
                            display_data.append(data)
                            print(f"📈 Display data: {list(data.keys())}")
                    
                    elif msg_type == 'error':
                        # Handle execution errors
                        success = False
                        error_name = content.get('ename', 'Error')
                        error_value = content.get('evalue', '')
                        traceback = content.get('traceback', [])
                        
                        error_msg = f"{error_name}: {error_value}"
                        if traceback:
                            error_msg += "\n" + "\n".join(traceback)
                        
                        stderr_lines.append(error_msg)
                        print(f"❌ Execution error: {error_name}: {error_value}")
                    
                    elif msg_type == 'status':
                        # Check if execution is complete
                        execution_state = content.get('execution_state')
                        if execution_state == 'idle':
                            print("✅ Code execution completed")
                            break
                        elif execution_state == 'busy':
                            print("⏳ Kernel is busy executing...")
                
                except Exception as e:
                    # Check for timeout
                    if asyncio.get_event_loop().time() - start_time > timeout:
                        print(f"⏰ Code execution timed out after {timeout} seconds")
                        success = False
                        stderr_lines.append(f"Execution timed out after {timeout} seconds")
                        break
                    continue
            
            # Prepare result
            result = ExecutionResult(
                success=success,
                stdout="".join(stdout_lines),
                stderr="".join(stderr_lines),
                display_data=display_data,
                execution_count=execution_count
            )
            
            if success:
                print(f"✅ Code execution successful (execution count: {execution_count})")
            else:
                print(f"❌ Code execution failed")
            
            return result
            
        except Exception as e:
            print(f"❌ Unexpected error during code execution: {e}")
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=f"Unexpected execution error: {str(e)}",
                display_data=[],
                execution_count=0
            )
    
    def extract_dataframe_info(self, execution_result: ExecutionResult) -> Optional[Dict[str, Any]]:
        """
        Extract DataFrame information from execution results.
        
        Args:
            execution_result: Result from code execution
            
        Returns:
            Dictionary with DataFrame info if found
        """
        print("🔍 Extracting DataFrame information from execution result")
        
        try:
            # Look for DataFrame HTML representation in display data
            for data in execution_result.display_data:
                if 'text/html' in data:
                    html_content = data['text/html']
                    if '<table' in html_content and 'dataframe' in html_content.lower():
                        print("📊 Found DataFrame HTML representation")
                        return {
                            'type': 'dataframe_html',
                            'content': html_content
                        }
                
                if 'text/plain' in data:
                    text_content = data['text/plain']
                    if 'DataFrame' in text_content or 'dtype:' in text_content:
                        print("📋 Found DataFrame text representation")
                        return {
                            'type': 'dataframe_text',
                            'content': text_content
                        }
            
            # Check stdout for DataFrame output
            if execution_result.stdout:
                stdout = execution_result.stdout
                if 'dtype:' in stdout or 'DataFrame' in stdout:
                    print("📄 Found DataFrame in stdout")
                    return {
                        'type': 'dataframe_stdout',
                        'content': stdout
                    }
            
            print("ℹ️ No DataFrame information found in execution result")
            return None
            
        except Exception as e:
            print(f"❌ Error extracting DataFrame info: {e}")
            return None
    
    def extract_plot_data(self, execution_result: ExecutionResult) -> Optional[Dict[str, Any]]:
        """
        Extract plot data from execution results.
        
        Args:
            execution_result: Result from code execution
            
        Returns:
            Dictionary with plot data if found
        """
        print("📈 Extracting plot data from execution result")
        
        try:
            for data in execution_result.display_data:
                # Look for Plotly JSON
                if 'application/json' in data:
                    json_data = data['application/json']
                    if isinstance(json_data, dict) and 'data' in json_data:
                        print("📊 Found Plotly JSON data")
                        return {
                            'type': 'plotly_json',
                            'content': json_data
                        }
                
                # Look for image data
                if 'image/png' in data:
                    print("🖼️ Found PNG image data")
                    return {
                        'type': 'image_png',
                        'content': data['image/png']
                    }
                
                if 'image/svg+xml' in data:
                    print("🎨 Found SVG image data")
                    return {
                        'type': 'image_svg',
                        'content': data['image/svg+xml']
                    }
            
            print("ℹ️ No plot data found in execution result")
            return None
            
        except Exception as e:
            print(f"❌ Error extracting plot data: {e}")
            return None


# Global execution service instance (lazy)
_jupyter_service: Optional[JupyterExecutionService] = None


def get_jupyter_service() -> JupyterExecutionService:
    """Get the global Jupyter execution service instance with lazy initialization."""
    global _jupyter_service
    if _jupyter_service is None:
        print("🔄 Initializing JupyterExecutionService (lazy)...")
        _jupyter_service = JupyterExecutionService()
    return _jupyter_service
