# AI-Powered Logistics Assistant (Phase 1) - Modular Architecture

This project implements an AI-powered logistics assistant with a clean, modular architecture that automates dataset profiling, generates intelligent metadata, and provides comprehensive type conversion analysis.

## 🏗️ Architecture Overview

The application has been restructured into a modular design with clear separation of concerns:

```
app/
├── main.py                 # FastAPI application entry point
├── api/                    # API layer
│   ├── __init__.py
│   └── routes.py          # API endpoints and route handlers
├── config/                 # Configuration management
│   ├── __init__.py
│   └── settings.py        # Centralized settings with environment variables
├── models/                 # Data models and schemas
│   ├── __init__.py
│   ├── requests.py        # Request models for API endpoints
│   ├── responses.py       # Response models for API endpoints
│   └── schemas.py         # Core data schemas and Pydantic models
├── services/               # Business logic layer
│   ├── __init__.py
│   ├── agent_service.py   # AI agent for metadata generation
│   └── profiling_service.py # Comprehensive data profiling with type conversion
├── utils/                  # Utility functions
│   ├── __init__.py
│   ├── data_utils.py      # Data processing utilities
│   ├── file_utils.py      # File handling utilities
│   └── validation_utils.py # Validation and parsing utilities
└── prompts/                # LLM prompt templates
    ├── __init__.py
    ├── metadata_prompts.py # Prompts for metadata generation
    └── relationship_prompts.py # Prompts for relationship inference
```

## 🚀 Features

### Core Features (Implemented)
- **Automated Data Profiling**: Comprehensive analysis of CSV datasets
- **AI-Powered Metadata Generation**: Uses LLM to generate human-readable descriptions
- **Type Conversion Analysis**: Advanced type inference and correction suggestions
- **Relationship Inference**: AI-powered analysis to identify entity relationships
- **RESTful API**: Clean FastAPI endpoints for dataset analysis

### Enhanced Features (New in Modular Version)
- **Centralized Configuration**: Environment-based settings management
- **Comprehensive Type Analysis**: Merged and enhanced type conversion capabilities
- **Modular Services**: Clean separation of profiling and AI services
- **Improved Error Handling**: Better error messages and graceful degradation
- **Extensible Architecture**: Easy to add new features and services

## 📋 Requirements

```
fastapi
uvicorn[standard]
pandas
langchain
langchain-openai
langgraph
python-dotenv
numpy
pydantic
pydantic-settings
```

## ⚙️ Configuration

Create a `.env` file in the project root:

```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.0

# Application Configuration
APP_TITLE=AI-Powered Logistics Assistant (Phase 1)
APP_VERSION=1.0.0
DEBUG=false

# Data Processing Configuration
NUMERIC_THRESHOLD=0.8
DATETIME_THRESHOLD=0.7
CATEGORICAL_THRESHOLD=50
```

## 🚀 Getting Started

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up Environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your OpenAI API key
   ```

3. **Run the Application**:
   ```bash
   python -m app.main
   # or
   uvicorn app.main:app --reload
   ```

4. **Access the API**:
   - API Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

## 📚 API Usage

### Analyze Dataset
```bash
curl -X POST "http://localhost:8000/v1/analyze" \
     -H "Content-Type: application/json" \
     -d '{"file_path": "datasets/sample_logistics.csv"}'
```

### Finalize Metadata
```bash
curl -X POST "http://localhost:8000/v1/metadata/finalize" \
     -H "Content-Type: application/json" \
     -d '{
       "dataset_name": "sample_logistics.csv",
       "final_metadata": {
         "dataset_description": "Logistics delivery data",
         "columns": [...]
       }
     }'
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Test modular structure
python test_modular_structure.py

# Test API endpoints (requires OpenAI API key)
python test_api.py
```

## 🔄 Migration from Legacy Code

The modular restructure maintains full backward compatibility while providing better organization, enhanced maintainability, improved testing capabilities, and centralized configuration management.

### Key Changes:
- `profiling.py` → `services/profiling_service.py` (enhanced with type conversion)
- `agent.py` → `services/agent_service.py` (improved structure)
- `type_conversion.py` → Merged into `profiling_service.py`
- Added comprehensive models, utilities, and configuration management

## 🚀 Phase 2: Natural Language Querying (NEW!)

Phase 2 introduces a sophisticated multi-agent system that allows users to query datasets using natural language. The system uses LangGraph to orchestrate multiple AI agents that work together to understand queries, generate code, execute it safely, and provide comprehensive responses.

### 🤖 Multi-Agent Architecture

The system employs 5 specialized agents:

1. **Planner Agent**: Breaks down user queries into sequential, actionable steps
2. **Code Generation Agent**: Generates Python code using ReAct methodology
3. **Error Analysis Agent**: Diagnoses and suggests fixes for failed code execution
4. **Chart Generation Agent**: Creates Plotly visualizations for results
5. **Final Response Agent**: Synthesizes findings into human-readable summaries

### 🔄 Real-Time Streaming

- **WebSocket Integration**: Real-time streaming of agent thoughts, code generation, and execution results
- **Live Updates**: Users see the AI's reasoning process as it happens
- **Interactive Sessions**: Persistent sessions with Jupyter kernel state management

### 🛡️ Safe Code Execution

- **Jupyter Sandbox**: Isolated execution environment using jupyter_client
- **Session Management**: Each user gets a dedicated Jupyter kernel
- **State Persistence**: Variables and data persist across queries within a session
- **Error Recovery**: Automatic error analysis and code correction

### 📊 Advanced Features

- **Parquet Storage**: Efficient data storage and retrieval
- **Chart Generation**: Automatic visualization creation with Plotly
- **Conversation History**: Context-aware responses based on previous interactions
- **Performance Monitoring**: Comprehensive logging and performance tracking

### 🔌 Phase 2 API Endpoints

#### Start a Query Session
```bash
POST /v2/query
{
  "session_id": "optional-existing-session-id",
  "dataset_name": "sample_logistics.csv",
  "query": "What is the average delivery time by city?",
  "conversation_history": []
}
```

#### WebSocket Streaming
```bash
ws://localhost:8000/v2/stream/{session_id}
```

Send messages:
```json
{
  "type": "query",
  "query": "Show me the top 5 drivers by performance",
  "conversation_history": []
}
```

Receive real-time updates:
```json
{
  "type": "thought",
  "payload": "I need to analyze driver performance metrics...",
  "timestamp": "2025-08-10T14:30:00",
  "step_index": 1
}
```

#### Session Management
```bash
GET /v2/sessions                    # List active sessions
DELETE /v2/sessions/{session_id}    # Cleanup specific session
POST /v2/sessions/cleanup           # Cleanup inactive sessions
```

### 🎯 Example Usage Flow

1. **Start Session**: POST to `/v2/query` with your dataset and question
2. **Connect WebSocket**: Use the returned WebSocket URL
3. **Send Query**: Send your natural language query via WebSocket
4. **Watch Magic**: See real-time agent thoughts, code generation, and execution
5. **Get Results**: Receive final analysis with charts and explanations

## 📄 Project Structure

```
app/
├── main.py                 # FastAPI application with both phases
├── api/                    # API layer
│   ├── routes.py          # Phase 1 endpoints
│   └── phase2_routes.py   # Phase 2 endpoints
├── config/                 # Configuration management
├── models/                 # Data models and schemas
│   ├── requests.py        # Phase 1 models
│   ├── responses.py       # Phase 1 models
│   ├── schemas.py         # Core schemas
│   └── phase2_models.py   # Phase 2 models
├── services/               # Business logic layer
│   ├── profiling_service.py    # Enhanced profiling with type conversion
│   ├── agent_service.py        # Phase 1 AI agent
│   ├── session_service.py      # Phase 2 session management
│   ├── jupyter_service.py      # Phase 2 code execution
│   ├── multi_agent_service.py  # Phase 2 multi-agent system
│   └── websocket_service.py    # Phase 2 real-time streaming
├── utils/                  # Utility functions
│   ├── data_utils.py      # Data processing
│   ├── file_utils.py      # File operations
│   ├── validation_utils.py # Validation helpers
│   └── logging_utils.py   # Comprehensive logging
└── prompts/                # LLM prompt templates
    ├── metadata_prompts.py     # Phase 1 prompts
    ├── relationship_prompts.py # Phase 1 prompts
    └── phase2_prompts.py       # Phase 2 agent prompts
```

### 📁 Additional Directories
- `datasets/`: Place CSV files here for analysis
- `metadata/`: Saved finalized metadata JSON files (Phase 1)
- `temp_data/`: Session data storage (Phase 2)
- Legacy files preserved as `*_old.py` for reference
