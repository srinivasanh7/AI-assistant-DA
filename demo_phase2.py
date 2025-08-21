"""Demo script for Phase 2 Natural Language Querying."""

import asyncio
import json
import os
import time
from typing import Dict, Any

import websockets
from fastapi.testclient import TestClient


async def demo_websocket_interaction():
    """Demonstrate WebSocket interaction with the multi-agent system."""
    print("🎭 Phase 2 WebSocket Demo")
    print("=" * 50)
    
    # Note: This demo shows the structure but requires a running server
    # and OpenAI API key to actually work
    
    print("📋 Demo Flow:")
    print("1. Start a query session via REST API")
    print("2. Connect to WebSocket for real-time streaming")
    print("3. Send natural language query")
    print("4. Receive real-time agent updates")
    print("5. Get final results with charts")
    
    print("\n🔗 Example REST API Call:")
    print("POST /v2/query")
    example_request = {
        "dataset_name": "sample_logistics.csv",
        "query": "What is the average delivery time by city?",
        "conversation_history": []
    }
    print(json.dumps(example_request, indent=2))
    
    print("\n📡 Example WebSocket Messages:")
    
    # Example query message
    query_message = {
        "type": "query",
        "query": "Show me the top 5 drivers by performance",
        "conversation_history": []
    }
    print(f"📤 Send: {json.dumps(query_message, indent=2)}")
    
    # Example streaming responses
    example_responses = [
        {
            "type": "log",
            "payload": "🎯 Starting planning phase...",
            "timestamp": "2025-08-10T14:30:00"
        },
        {
            "type": "plan",
            "payload": [
                "Filter the DataFrame to include only driver performance data",
                "Calculate performance metrics for each driver",
                "Sort drivers by performance score in descending order",
                "Select the top 5 drivers",
                "Display the results with driver names and scores"
            ],
            "timestamp": "2025-08-10T14:30:05"
        },
        {
            "type": "thought",
            "payload": "I need to analyze driver performance. Let me start by examining the available columns and calculating a performance score.",
            "timestamp": "2025-08-10T14:30:10",
            "step_index": 0
        },
        {
            "type": "code",
            "payload": "print('Analyzing driver performance data...')\nprint('Available columns:', list(df.columns))\nprint('Dataset shape:', df.shape)",
            "timestamp": "2025-08-10T14:30:15",
            "step_index": 0
        },
        {
            "type": "execution_success",
            "payload": "Analyzing driver performance data...\nAvailable columns: ['DriverID', 'OnTimeDelivery', 'Distance_km', 'FuelConsumption_litre']\nDataset shape: (1000, 4)",
            "timestamp": "2025-08-10T14:30:20",
            "step_index": 0
        },
        {
            "type": "chart",
            "payload": {
                "type": "plotly_json",
                "data": {"data": [{"x": ["Driver1", "Driver2"], "y": [95, 87], "type": "bar"}]}
            },
            "timestamp": "2025-08-10T14:30:45"
        },
        {
            "type": "final_response",
            "payload": "Based on the analysis, here are the top 5 drivers by performance: Driver1 (95% score), Driver2 (87% score), Driver3 (82% score), Driver4 (78% score), and Driver5 (75% score). The performance score is calculated based on on-time delivery rate and fuel efficiency. I have also generated a chart to visualize this information.",
            "timestamp": "2025-08-10T14:30:50"
        }
    ]
    
    for i, response in enumerate(example_responses, 1):
        print(f"\n📥 Receive {i}: {json.dumps(response, indent=2)}")
        time.sleep(0.5)  # Simulate real-time streaming
    
    print("\n✅ Demo completed!")
    print("\n🚀 To run this for real:")
    print("1. Set your OPENAI_API_KEY in .env file")
    print("2. Run: python -m app.main")
    print("3. Use the API endpoints or build a frontend")


def demo_api_structure():
    """Demonstrate the API structure without requiring a server."""
    print("\n🏗️ Phase 2 API Structure Demo")
    print("=" * 50)
    
    print("📋 Available Endpoints:")
    
    endpoints = [
        {
            "method": "POST",
            "path": "/v2/query",
            "description": "Start a new query session",
            "example_request": {
                "dataset_name": "logistics_data.csv",
                "query": "What are the peak delivery hours?",
                "session_id": None
            },
            "example_response": {
                "session_id": "abc-123-def",
                "websocket_url": "ws://localhost:8000/v2/stream/abc-123-def"
            }
        },
        {
            "method": "WebSocket",
            "path": "/v2/stream/{session_id}",
            "description": "Real-time streaming of agent execution",
            "message_types": [
                "thought", "code", "log", "error", "table", 
                "chart", "final_response", "plan", "execution_start", 
                "execution_success", "execution_error"
            ]
        },
        {
            "method": "GET",
            "path": "/v2/sessions",
            "description": "List all active sessions",
            "example_response": {
                "active_sessions": 3,
                "websocket_connections": 2,
                "sessions": [
                    {
                        "session_id": "abc-123",
                        "dataset_name": "logistics.csv",
                        "created_at": "2025-08-10T14:00:00",
                        "has_websocket": True
                    }
                ]
            }
        },
        {
            "method": "DELETE",
            "path": "/v2/sessions/{session_id}",
            "description": "Cleanup a specific session"
        },
        {
            "method": "POST",
            "path": "/v2/sessions/cleanup",
            "description": "Cleanup inactive sessions"
        }
    ]
    
    for endpoint in endpoints:
        print(f"\n🔗 {endpoint['method']} {endpoint['path']}")
        print(f"   📝 {endpoint['description']}")
        
        if 'example_request' in endpoint:
            print(f"   📤 Request: {json.dumps(endpoint['example_request'], indent=6)}")
        
        if 'example_response' in endpoint:
            print(f"   📥 Response: {json.dumps(endpoint['example_response'], indent=6)}")
        
        if 'message_types' in endpoint:
            print(f"   📡 Message Types: {', '.join(endpoint['message_types'])}")


def demo_agent_workflow():
    """Demonstrate the multi-agent workflow."""
    print("\n🤖 Multi-Agent Workflow Demo")
    print("=" * 50)
    
    workflow_steps = [
        {
            "agent": "Planner Agent",
            "emoji": "🎯",
            "task": "Analyze user query and create step-by-step plan",
            "input": "User query + dataset metadata + conversation history",
            "output": "Sequential list of actionable steps"
        },
        {
            "agent": "Code Generation Agent",
            "emoji": "💻",
            "task": "Generate Python code for current step using ReAct methodology",
            "input": "Current step + full plan + execution history",
            "output": "Thought process + Python code"
        },
        {
            "agent": "Code Executor",
            "emoji": "🚀",
            "task": "Execute code in Jupyter kernel safely",
            "input": "Generated Python code",
            "output": "Execution results (stdout, stderr, display data)"
        },
        {
            "agent": "Error Analysis Agent",
            "emoji": "🔍",
            "task": "Diagnose errors and suggest fixes (if needed)",
            "input": "Failed code + error message + metadata",
            "output": "Error diagnosis + fix suggestion"
        },
        {
            "agent": "Chart Generation Agent",
            "emoji": "📊",
            "task": "Create Plotly visualizations for final results",
            "input": "User query + final data",
            "output": "Plotly chart code"
        },
        {
            "agent": "Final Response Agent",
            "emoji": "📝",
            "task": "Synthesize findings into human-readable summary",
            "input": "User query + final data + chart availability",
            "output": "Comprehensive response"
        }
    ]
    
    for i, step in enumerate(workflow_steps, 1):
        print(f"\n{step['emoji']} Step {i}: {step['agent']}")
        print(f"   🎯 Task: {step['task']}")
        print(f"   📥 Input: {step['input']}")
        print(f"   📤 Output: {step['output']}")
    
    print(f"\n🔄 The workflow uses LangGraph for orchestration and includes:")
    print("   • Conditional routing based on execution results")
    print("   • Error recovery with automatic retry logic")
    print("   • Real-time streaming of all agent activities")
    print("   • State persistence across the entire workflow")


def main():
    """Run all demos."""
    print("🎭 AI-Powered Logistics Assistant - Phase 2 Demo")
    print("=" * 60)
    
    demo_api_structure()
    demo_agent_workflow()
    
    print("\n" + "=" * 60)
    print("🎉 Phase 2 Implementation Complete!")
    print("\n✨ Key Features Implemented:")
    print("   • 🤖 Multi-agent system with 5 specialized agents")
    print("   • 📡 Real-time WebSocket streaming")
    print("   • 🛡️ Safe Jupyter sandbox execution")
    print("   • 📊 Automatic chart generation")
    print("   • 🔄 Error recovery and retry logic")
    print("   • 📝 Comprehensive logging and monitoring")
    print("   • 🎯 Session management with state persistence")
    
    print("\n🚀 Ready to process natural language queries!")
    
    # Run the async demo
    asyncio.run(demo_websocket_interaction())


if __name__ == "__main__":
    main()
