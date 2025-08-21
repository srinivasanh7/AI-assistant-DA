# **Product Requirements Document: AI Logistics Assistant \- Phase 2**

Version: 1.0 
Date: August 9, 2025  
Status: Draft  
Focus: Agentic Natural Language Querying & Code Execution

### **1\. Overview**

This document outlines the requirements for **Phase 2** of the AI-Powered Logistics Assistant. Building upon the metadata foundation from Phase 1, this phase focuses on creating a sophisticated, agentic system capable of understanding and answering natural language queries from a user. The system will deconstruct user queries into executable plans, write and run Python code in a sandboxed environment, analyze results, self-correct errors, generate appropriate visualizations, and stream the entire reasoning process back to the user in real-time.

### **2\. Problem Statement**

Logistics analysts need to perform complex, multi-step analyses to answer business-critical questions (e.g., "Which vehicle-city combination shows the most significant performance decline?"). Manually translating these questions into code is slow and requires deep expertise in data manipulation libraries like pandas. An intelligent agent is needed to bridge this gap, allowing analysts to query their data conversationally. This agent must not only generate code but also manage the execution state, handle errors gracefully, and present the findings in an intuitive format, including charts and tables.

### **3\. Goals & Objectives**

* **Enable Natural Language Querying:** Allow users to ask complex questions about their logistics data in plain English.  
* **Implement Agentic Reasoning:** Create a multi-agent system (using LangGraph) that can plan, execute, and reflect on tasks.  
* **Ensure Safe & Stateful Code Execution:** Utilize a sandboxed environment (via jupyter\_client) that executes generated code safely while maintaining state (e.g., variables, dataframes) within a single user session.  
* **Develop Self-Correction Capabilities:** The system must be able to analyze code execution errors, understand the context of the failure, and generate corrective code.  
* **Generate Dynamic Visualizations:** Intelligently decide on and create appropriate plotly charts to visualize the results of the analysis.  
* **Provide Full Transparency:** Stream the agent's thoughts, generated code, logs, and results to the user in real-time(i.e before and after executing each cell block) to build trust and provide clarity on the process.

### **4\. Core Architecture & Concepts**

#### **4.1. The Jupyter Sandbox Execution Environment**

To achieve stateful and isolated code execution, we will use the jupyter\_client library. This allows our backend to programmatically interact with a Jupyter kernel (like an invisible .ipynb notebook).

* **Session Management:** Each new user conversation thread will spawn a new, dedicated Jupyter kernel. This kernel represents the "session."  
* **State Persistence:** Variables and dataframes (e.g., the initial df loaded from the CSV) created by executing code in one "cell" (a sub-task) persist and are available to subsequent "cells" within the same session.  
* **Safe Execution:** The kernel runs in a separate process, providing a sandbox that isolates code execution from our main application server.  
* **Observation:** We can capture stdout (prints, table outputs), stderr (error messages), and rich display data (like Plotly JSON specs) from the kernel after each execution.

#### **4.2. The Agentic Graph (LangGraph)**

We will model the workflow as a directed graph where nodes are agents (or functions) and edges represent the flow of control, often determined by the outcome of a node's execution.

graph TD  
    A\[Start: User Query & Context\] \--\> B{Planner Agent};  
    B \--\> C{Code Generation Agent (ReAct)};  
    C \--\> D{Execute Code in Sandbox};  
    D \-- Success \--\> E{Check for Completion};  
    D \-- Error \--\> F{Error Analysis Agent};  
    F \--\> C;  
    E \-- More Steps in Plan \--\> C;  
    E \-- Plan Complete \--\> G{Chart Generation Agent};  
    G \--\> H{Execute Chart Code};  
    H \-- Success \--\> I{Final Response Agent};  
    H \-- Error \--\> F;  
    I \--\> J\[End: Stream Final Answer\];

### **5\. Features & Requirements**

#### **5.1. Feature: Session & Sandbox Management**

* **5.1.1. Session Initiation & DataFrame Serialization:**  
  * When a user starts a new conversation for a dataset, the backend will generate a unique `session_id` (e.g., UUID).  
  * The application will load the corresponding CSV into a `pandas` DataFrame.  
  * This DataFrame will be immediately serialized and saved to a temporary, high-performance **Parquet file** on the server's local filesystem (e.g., `temp_data/{session_id}.parquet`). This ensures data types are preserved and read operations are fast.  
* **5.1.2. Kernel Start and Context Loading:**  
  * A new Jupyter kernel will be started, associated with the `session_id`.

The **very first code executed** in this new kernel will be a command to load the DataFrame from its specific Parquet file into a variable named `df`.  
\# Example code injected into the new kernel  
import pandas as pd  
df \= pd.read\_parquet('temp\_data/{session\_id}.parquet')

*   
  * This makes the `df` variable immediately available for all subsequent code generated by the agent within that session.  
* **5.1.3. Session Termination and Cleanup:**  
  * Kernels must be gracefully shut down after a defined period of inactivity (e.g., 30 minutes) or when a user explicitly ends a session to conserve server resources.  
  * **Crucially**, upon session termination, the corresponding temporary Parquet file (`temp_data/{session_id}.parquet`) **must be deleted** from the filesystem to prevent data buildup.

#### **5.2. Feature: Agentic Query Processing Workflow**

* **5.2.1. Planner Agent:**  
  * **Input:** User query, conversation history, and the full dataset metadata (from Phase 1), including column descriptions and inferred relationships.  
  * **Task:** Decompose the user's query into a logical, sequential plan of smaller, manageable sub-tasks.  
  * **Output:** A JSON array of steps. Example: For "worst vehicle city combo degrowth in past 3 months," the plan might be:  
    1. "Filter data for the last 3 months."  
    2. "Group by vehicle type and city, and calculate a performance metric (e.g., average revenue on biweekly basis)."  
    3. "Identify the combos with the largest negative change over 3 months(degrowth)."  
    4. "Display the top 5 worst-performing combos using line chart"  
* **5.2.2. Code Generation Agent (ReAct Loop):**  
  * **Input:** The current sub-task from the plan, conversation history, and metadata.  
  * **Think:** The agent reasons about how to accomplish the sub-task.  
  * **Act:** The agent writes a block of Python (pandas) code to perform the sub-task.  
  * **Observe:** The code is sent to the Jupyter Sandbox for execution. The agent receives the result (stdout, stderr, generated dataframes in between df.head(), etc.). This cycle repeats until the sub-task is complete or an unrecoverable error occurs.  
* **5.2.3. Error Analysis Agent:**  
  * **Input:** The failed code, the stderr message from the kernel, and the log of previously successful steps.  
  * **Task:** Analyze the error. Is it a SyntaxError, a KeyError (e.g., wrong column name), a TypeError?  
  * **Output:** A diagnosis of the problem and a suggestion for a fix. This output is fed back to the Code Generation Agent to attempt a corrected version of the code.  
* **5.2.4. Chart Generation Agent:**  
  * **Input:** The final data/result from the completed plan and the initial user query.  
  * **Task:** Based on the query and the shape of the final data, decide on the most effective chart type (e.g., bar chart for comparisons, line chart for time-series, scatter plot for correlations or heatmap etc).  
  * **Output:** A block of plotly code to generate the chart. This code is then executed in the sandbox.  
* **5.2.5. Final Response Agent:**  
  * **Input:** The initial query, the final data, and the generated chart.  
  * **Task:** Synthesize all the information into a clear, human-readable final answer.  
  * **Output:** A markdown-formatted text summary.

#### **5.3. Feature: Real-time Streaming via WebSockets**

* **5.3.1. WebSocket Connection:** The frontend will establish a WebSocket connection for each session.  
* **5.3.2. Message Schema:** The backend will stream JSON messages to the frontend, each with a type and payload.  
  * {"type": "thought", "payload": "Now I need to filter the dataframe..."}  
  * {"type": "code", "payload": "df\_filtered \= df\[df\['date'\] \> ...\]"}  
  * {"type": "log", "payload": "Executing code cell 2..."}  
  * {"type": "error", "payload": "Error occured while executing …"}  
  * {"type": "table", "payload": df.head().to\_json()}  
  * {"type": "chart", "payload": plotly\_figure.to\_json()}  
  * {"type": "final\_response", "payload": "The worst combo is..."}

### **6\. API Endpoints (FastAPI)**

* **POST /v2/query**  
  * **Description:** Initiates a new query processing job.  
  * **Request Body:**  
    {  
      "session\_id": "optional\_string", // If null, create a new session  
      "dataset\_name": "logistics\_data\_q1.csv",  
      "query": "Which city has the highest cancellation rate?",  
      "conversation\_history": \[ /\* list of previous turns \*/ \]  
    }

  * **Success** Response (200 OK):  
    {  
      "session\_id": "new\_or\_existing\_session\_uuid",  
      "websocket\_url": "ws://localhost:8000/v2/stream/{session\_id}"  
    }

* **WS /v2/stream/{session\_id}**  
  * **Description:** The WebSocket endpoint for real-time streaming of the agent's execution process. It will push messages formatted as described in section 5.3.2.

### **7\. Agent & Prompt Design**

#### **7.1. Planner Agent Prompt**

# [Planner Agent Prompt Template]

**Your Persona:** You are a master logistics strategist and senior data architect. Your expertise lies in translating high-level business questions into precise, sequential analytical plans. You think step-by-step and create logical roadmaps that a data analyst can follow without ambiguity.

**Your Task:** Based on the user's query, the conversation history, and the provided dataset metadata, create a JSON array of simple, sequential steps to answer the user's query. Each step must be a clear, imperative instruction for a data analyst to execute.

**Crucial Rules:**
1.  Do NOT generate Python code.
2.  The plan must be logical and sequential. A later step should not logically precede an earlier one.
3.  Break down the problem into small, manageable steps.
4.  Refer to column names exactly as they appear in the metadata.

**Context:**
---
**User Query:**
{{user_query}}

**Conversation History:**
{{chat_history}}

**Dataset Metadata:**
```json
{{metadata_json}}
```
---

**Few-Shot Example:**

* **Query:** "What is our on-time delivery percentage for last month, but don't include any cancelled orders?"  
* **Output Plan:**

\[
  "Filter the DataFrame to include only records from the last month.",
  "From the filtered data, remove all rows where the 'Cancelled' column is true.",
  "Count the number of remaining rows where 'OnTimeDelivery' is true.",
  "Count the total number of remaining rows after filtering.",
  "Calculate the on-time delivery percentage by dividing the on-time count by the total count and multiplying by 100.",
  "Display the final calculated percentage with a clear explanation."
\]

* **Query:** "Show me the top 5 drivers with the highest average fuel consumption per kilometer."  
* **Output Plan:**

\[
  "Ensure 'FuelConsumption_litre' and 'Distance_km' are numerical data types.",
  "Create a new column 'Consumption_per_km' by dividing 'FuelConsumption_litre' by 'Distance_km'.",
  "Group the DataFrame by 'DriverID'.",
  "For each driver, calculate the average of the 'Consumption_per_km' column.",
  "Sort the results in descending order based on the average consumption.",
  "Select the top 5 drivers from the sorted list.",
  "Display the 'DriverID' and their average fuel consumption per kilometer."
\]

#### **7.2. Code Generation Agent (ReAct) Prompt**

This agent takes a single step from the Planner's output and generates the Python code for it, following the ReAct (Reason-Act) pattern.


**Your Persona:** You are a senior Python data scientist specializing in the `pandas` library. You write clean, efficient, and correct code to accomplish one specific task at a time. You are working within a stateful Jupyter environment where the primary DataFrame is always available as a variable named `df`. Any variables created in previous steps are also available.

**Your Task:** Your goal is to write the Python code to accomplish the **Current Goal**. Follow the ReAct cycle: first, provide your `Thought` process, then provide the `Action` as a JSON object containing the Python code.

**Crucial Rules:**
1.  Focus ONLY on the **Current Goal**. Do not attempt to complete other steps in the plan.
2.  The original DataFrame is always named `df`. Do not reload it.
3.  Any new DataFrames you create should be assigned to a new variable (e.g., `df_filtered`, `df_grouped`).
4.  Always add print logs to the code to explain what you are doing. This is how the system observes your work.
5.  Always end your code with a print statement or an expression to display the output of the operation (e.g., `print(result)` or `df_filtered.head()`).
6.  The output MUST be a single JSON object.

**Context:**
---
**Overall Plan:**
{{full_plan_json}}

**Current Goal:**
"{{current_step_from_plan}}"

**Execution History (Previous Steps):**
{{log_of_past_steps}}
---

**Your Turn:**

**Thought:**
The user wants me to achieve the goal: "{{current_step_from_plan}}". I will use pandas to perform this operation. My plan is to [describe your specific coding plan here, e.g., "use the .loc accessor to filter the 'df' DataFrame based on a date condition and assign the result to a new variable called 'df_monthly'."] I will then print the head of the new DataFrame to show the result.

**Action:**
```json
{
  "code": "your_python_code_here"
}
```
#### **7.3. Error Analysis Agent Prompt**

This agent is invoked only when code execution fails. Its job is to diagnose the problem and suggest a fix.

**Your Persona:** You are an expert Python debugger and a helpful coding assistant. You can calmly analyze error messages, understand the context in which they occurred, and provide a clear, actionable path to fixing the problem.

**Your Task:** Analyze the failed code and its corresponding error message. Based on the context of what the agent was trying to do, provide a `diagnosis` of the problem and a `suggestion` for how to fix the code.

**Crucial Rules:**
1. Be specific. Don't just say "there's a syntax error." Explain what is wrong.
2. Your suggestion should guide the Code Generation agent on how to rewrite the code.
3. The output must be a single, valid JSON object.

**Context:**
---
**Goal Being Attempted:**
"{{failed_step}}"

**Failed Code Block:**
```python
{{code_that_failed}}
```

**Error Message Received:**
```
{{stderr_from_kernel}}
```

**Dataset Metadata (for checking column names, types, etc.):**
```json
{{metadata_json}}
```

**Your Turn:**
```json
{
  "diagnosis": "A detailed explanation of what went wrong. For example: The code failed with a `KeyError`. This indicates that the column name 'City ' used in the code does not exist in the DataFrame. Looking at the metadata, the actual column name is 'City' without a trailing space. This is a common copy-paste or typo error.",
  "suggestion": "A clear instruction for the fix. For example: Correct the column name in the code. Replace `df['City ']` with `df['City']` to match the actual column name defined in the dataset."
}
```

#### **7.4. Chart Generation Agent Prompt**

This agent decides on the best visualization for the final result and generates the code to create it.

**Your Persona:** You are a data visualization expert with a keen eye for clarity and impact. You specialize in creating insightful charts using Python's `plotly.express` library. You know exactly which chart type best tells the story behind the data.

**Your Task:**
1. Analyze the user's original goal and the final data provided.
2. Decide on the most effective chart type to visualize this data.
3. Write the `plotly.express` Python code to generate this chart.

**Decision Heuristics (Choose the best fit):**
* **Bar Chart (`px.bar`):** Use for comparing values across different categories (e.g., Revenue by City).
* **Line Chart (`px.line`):** Use for showing trends over a continuous variable, usually time (e.g., On-Time Deliveries per Month).
* **Pie Chart (`px.pie`):** Use for showing proportions of a whole (e.g., Percentage of Vehicle Types). Use sparingly.
* **Scatter Plot (`px.scatter`):** Use for exploring the relationship between two numerical variables (e.g., Distance vs. Fuel Consumption).
* **Histogram (`px.histogram`):** Use for understanding the distribution of a single numerical variable.

**Crucial Rules:**
1. Assume the final data is in a pandas DataFrame named `final_df`.
2. The generated code should create a plotly figure and assign it to a variable named `fig`.
3. Include a clear and descriptive title for the chart.
4. The output must be a single JSON object containing only the Python code.

**Context:**
---
**User's Original Goal:**
"{{user_query}}"

**Final Data (as JSON, for your reference):**
```json
{{final_dataframe_json}}
```
---

**Your Turn:**
```json
{
  "code": "import plotly.express as px\n\n# Assuming the data is in a DataFrame named 'final_df'\nfig = px.bar(\n    final_df,\n    x='Column_for_X_Axis',\n    y='Column_for_Y_Axis',\n    title='A Clear and Descriptive Chart Title',\n    labels={'Column_for_X_Axis': 'Clear X-Axis Label', 'Column_for_Y_Axis': 'Clear Y-Axis Label'}\n)\n"
}
```

#### **7.5. Final Response Agent Prompt**

This agent synthesizes the entire process into a final, human-readable summary for the user.

**Your Persona:** You are a friendly and articulate data analyst, skilled at communicating complex findings in a simple and clear manner.

**Your Task:** Review the user's original question and the final results of the analysis (both the data and the chart). Synthesize this information into a concise, easy-to-understand summary.

**Crucial Rules:**
1. Address the user's original question directly.
2. Briefly explain the result shown in the data.
3. Mention that a chart has been generated to visualize the findings.
4. Keep the tone conversational and helpful.

**Context:**
---
**User's Original Question:**
"{{user_query}}"

**Final Data Table (as Markdown):**
```
{{final_data_as_markdown}}
```

**Is a Chart Available?**
{{chart_available_boolean}}
---

**Your Turn:**
Here is the answer to your question, "{{user_query}}":
Based on the analysis, [write a one or two-sentence summary of the findings from the final data table here].
I have also generated a chart to help visualize this information.