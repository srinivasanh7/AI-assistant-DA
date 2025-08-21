"""Comprehensive logging utilities for Phase 2."""

import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        # Add color to the log level
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"
        
        return super().format(record)


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Set up comprehensive logging for the application."""
    
    # Create logger
    logger = logging.getLogger("rusty_reimagined")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    
    # Create formatter
    formatter = ColoredFormatter(
        fmt='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    return logger


class AgentLogger:
    """Specialized logger for agent operations."""
    
    def __init__(self, session_id: str, agent_name: str):
        """Initialize agent logger."""
        self.session_id = session_id
        self.agent_name = agent_name
        self.logger = logging.getLogger(f"agent.{agent_name}")
        
    def log_start(self, operation: str, **kwargs) -> None:
        """Log the start of an operation."""
        extra_info = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
        message = f"🚀 [{self.session_id}] {self.agent_name} starting: {operation}"
        if extra_info:
            message += f" | {extra_info}"
        self.logger.info(message)
    
    def log_success(self, operation: str, result: Any = None, **kwargs) -> None:
        """Log successful completion of an operation."""
        extra_info = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
        message = f"✅ [{self.session_id}] {self.agent_name} completed: {operation}"
        if result:
            message += f" | result: {str(result)[:100]}..."
        if extra_info:
            message += f" | {extra_info}"
        self.logger.info(message)
    
    def log_error(self, operation: str, error: Exception, **kwargs) -> None:
        """Log an error during an operation."""
        extra_info = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
        message = f"❌ [{self.session_id}] {self.agent_name} error in: {operation} | error: {str(error)}"
        if extra_info:
            message += f" | {extra_info}"
        self.logger.error(message)
    
    def log_thought(self, thought: str) -> None:
        """Log agent thought process."""
        message = f"🧠 [{self.session_id}] {self.agent_name} thought: {thought}"
        self.logger.info(message)
    
    def log_code_generation(self, code: str) -> None:
        """Log generated code."""
        code_preview = code.replace('\n', '\\n')[:100]
        message = f"💻 [{self.session_id}] {self.agent_name} generated code: {code_preview}..."
        self.logger.info(message)
    
    def log_execution(self, success: bool, output: str = "", error: str = "") -> None:
        """Log code execution results."""
        if success:
            output_preview = output.replace('\n', '\\n')[:100]
            message = f"🎯 [{self.session_id}] {self.agent_name} execution success: {output_preview}..."
        else:
            error_preview = error.replace('\n', '\\n')[:100]
            message = f"💥 [{self.session_id}] {self.agent_name} execution failed: {error_preview}..."
        self.logger.info(message)


class SessionLogger:
    """Specialized logger for session operations."""
    
    def __init__(self, session_id: str):
        """Initialize session logger."""
        self.session_id = session_id
        self.logger = logging.getLogger("session")
    
    def log_creation(self, dataset_name: str) -> None:
        """Log session creation."""
        message = f"🆕 Session created: {self.session_id} | dataset: {dataset_name}"
        self.logger.info(message)
    
    def log_kernel_start(self) -> None:
        """Log kernel startup."""
        message = f"🚀 Jupyter kernel started for session: {self.session_id}"
        self.logger.info(message)
    
    def log_kernel_stop(self) -> None:
        """Log kernel shutdown."""
        message = f"🛑 Jupyter kernel stopped for session: {self.session_id}"
        self.logger.info(message)
    
    def log_data_load(self, rows: int, columns: int) -> None:
        """Log data loading."""
        message = f"📊 Data loaded for session: {self.session_id} | {rows} rows, {columns} columns"
        self.logger.info(message)
    
    def log_cleanup(self) -> None:
        """Log session cleanup."""
        message = f"🧹 Session cleaned up: {self.session_id}"
        self.logger.info(message)
    
    def log_activity(self, activity: str) -> None:
        """Log session activity."""
        message = f"📝 Session activity: {self.session_id} | {activity}"
        self.logger.info(message)


class WebSocketLogger:
    """Specialized logger for WebSocket operations."""
    
    def __init__(self, session_id: str):
        """Initialize WebSocket logger."""
        self.session_id = session_id
        self.logger = logging.getLogger("websocket")
    
    def log_connection(self) -> None:
        """Log WebSocket connection."""
        message = f"🔗 WebSocket connected: {self.session_id}"
        self.logger.info(message)
    
    def log_disconnection(self) -> None:
        """Log WebSocket disconnection."""
        message = f"🔌 WebSocket disconnected: {self.session_id}"
        self.logger.info(message)
    
    def log_message_sent(self, message_type: str, payload_preview: str) -> None:
        """Log message sent to client."""
        message = f"📤 Message sent to {self.session_id} | type: {message_type} | payload: {payload_preview[:50]}..."
        self.logger.info(message)
    
    def log_message_received(self, message_type: str, payload_preview: str) -> None:
        """Log message received from client."""
        message = f"📨 Message received from {self.session_id} | type: {message_type} | payload: {payload_preview[:50]}..."
        self.logger.info(message)
    
    def log_error(self, error: str) -> None:
        """Log WebSocket error."""
        message = f"❌ WebSocket error for {self.session_id}: {error}"
        self.logger.error(message)


class PerformanceLogger:
    """Logger for performance monitoring."""
    
    def __init__(self):
        """Initialize performance logger."""
        self.logger = logging.getLogger("performance")
        self.start_times: Dict[str, datetime] = {}
    
    def start_timer(self, operation: str, session_id: str = None) -> None:
        """Start timing an operation."""
        key = f"{session_id}:{operation}" if session_id else operation
        self.start_times[key] = datetime.now()
        
        message = f"⏱️ Started timing: {operation}"
        if session_id:
            message += f" | session: {session_id}"
        self.logger.debug(message)
    
    def end_timer(self, operation: str, session_id: str = None) -> float:
        """End timing an operation and return duration."""
        key = f"{session_id}:{operation}" if session_id else operation
        
        if key not in self.start_times:
            self.logger.warning(f"⚠️ No start time found for operation: {operation}")
            return 0.0
        
        start_time = self.start_times.pop(key)
        duration = (datetime.now() - start_time).total_seconds()
        
        message = f"⏱️ Completed timing: {operation} | duration: {duration:.2f}s"
        if session_id:
            message += f" | session: {session_id}"
        self.logger.info(message)
        
        return duration
    
    def log_memory_usage(self, operation: str, memory_mb: float) -> None:
        """Log memory usage for an operation."""
        message = f"💾 Memory usage for {operation}: {memory_mb:.2f} MB"
        self.logger.info(message)


# Global logger instances
main_logger = setup_logging()
performance_logger = PerformanceLogger()


def get_agent_logger(session_id: str, agent_name: str) -> AgentLogger:
    """Get an agent logger instance."""
    return AgentLogger(session_id, agent_name)


def get_session_logger(session_id: str) -> SessionLogger:
    """Get a session logger instance."""
    return SessionLogger(session_id)


def get_websocket_logger(session_id: str) -> WebSocketLogger:
    """Get a WebSocket logger instance."""
    return WebSocketLogger(session_id)


def get_performance_logger() -> PerformanceLogger:
    """Get the performance logger instance."""
    return performance_logger
