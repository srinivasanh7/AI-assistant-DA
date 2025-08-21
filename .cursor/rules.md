# **Product Requirements Document: AI-Powered Logistics Assistant (Phase 1\)**

### **1\. Overview**

This document outlines the requirements for the initial phase of an **AI-Powered Logistics Assistant**. The primary goal of this phase is to create a robust backend service that can ingest a logistics dataset (in CSV format), perform an initial automated analysis, generate descriptive metadata using an AI agent, and facilitate a user feedback loop to refine and store this metadata. This foundational work will enable more complex, agentic analysis and visualization in subsequent phases.

### **2\. Problem Statement**

Logistics companies and analysts handle diverse datasets with varying schemas, inconsistent data types, and hidden categorical meanings. The initial process of understanding a new dataset—identifying its structure, assessing data quality, and deciphering column meanings—is manual, time-consuming, and requires domain expertise. This bottleneck slows down the time-to-insight and makes it difficult to quickly leverage data for operational improvements. We need an intelligent system that automates this initial data profiling and interpretation, setting a clean, well-understood foundation for advanced analytics.

### **3\. Goals & Objectives**

* **Automate Data Profiling:** Automatically analyze an uploaded CSV to determine its structure, data types, and basic statistics.  
* **Intelligent Metadata Generation:** Use an LLM-powered agent to generate human-readable descriptions for the dataset and its columns, including the meaning of categorical codes.  
* **Improve Data Quality:** Proactively identify and flag potential data quality issues, such as incorrect data types (e.g., numbers stored as text) and missing values.  
* **Establish a "Human-in-the-Loop" Workflow:** Create API endpoints to present the AI-generated analysis to a user for review, correction, and final approval.  
* **Persistent Memory:** Securely store the user-validated metadata for a given dataset, creating a reliable "source of truth" for future analytical tasks.

### **4\. User Persona**

* **Name:** Priya Sharma  
* **Role:** Logistics Data Analyst  
* **Goals:**  
  * Quickly understand the contents and quality of new datasets from different clients or departments.  
  * Reduce the time spent on data cleaning and preparation.  
  * Generate accurate reports and visualizations on key logistics KPIs like on-time delivery, cost per kilometer, and vehicle efficiency.  
* **Frustrations:**  
  * Receives CSV files where column names are cryptic (S\_Type, Dist\_KM) and data is messy (e.g., Duration\_min column contains "60 mins" instead of 60).  
  * Spends hours manually exploring the data, correcting types, and documenting findings before any real analysis can begin.

### **5\. Features & Requirements**

#### **5.1. Feature: Data Ingestion & Automated Profiling**

The system must ingest a CSV file and perform a comprehensive initial analysis.

* **5.1.1. File Handling:** The system will initially read a CSV file from a local directory (e.g., ./datasets/). The architecture should be flexible enough to support file uploads in the future.  
* **5.1.2. Column & Data Type Identification:**  
  * The system must parse the CSV and identify all column headers.  
  * Using pandas, it will infer the initial data type (object, int64, float64, datetime64) for each column.  
* **5.1.3. Data Quality Report Generation:**  
  * **Missing Values:** For each column, calculate the count and percentage of missing values.  
  * **Basic Statistics:** Generate descriptive statistics for the dataset (similar to pandas.DataFrame.describe(include='all')), including count, mean, std, min, max, unique values, and frequency for numerical and categorical columns.  
  * **Data Type Correction Suggestions:** The system must identify columns that are likely incorrect. For example, a column with object dtype containing mostly numerical strings ("55.5", "120", "85") should be flagged with a suggestion to convert it to a numerical type. This will be a key input for the user feedback loop.

#### **5.2. Feature: AI-Powered Metadata Generation**

An AI agent will enrich the basic profiling with semantic understanding.

* **5.2.1. Agent Initialization:** The system will use an agent (built with LangGraph/LangChain) configured with the persona of a "Senior Transportation Logistics Analyst."  
* **5.2.2. Contextual Input:** The agent will be provided with:  
  * The full list of column names.  
  * The inferred data types for each column.  
  * The top 10-20 rows of the dataset to provide context.  
  * For categorical columns, the list of unique values.  
* **5.2.3. Metadata Generation Task:** The agent's task is to output a structured JSON object containing:  
  * A high-level, one-paragraph dataset\_description.  
  * For each column:  
    * A clear, concise description of what the column likely represents.  
    * A standardized data\_type classification ('Numerical', 'Categorical', 'Datetime', 'ID', 'Text', 'Boolean').  
    * For categorical columns, a description for each unique value (e.g., for a column VehicleType with value 2W, the description would be "2 Wheeler").

#### **5.3. Feature: User Feedback & Metadata Finalization**

The system must allow a user to review, edit, and approve the AI-generated metadata.

* **5.3.1. Expose Analysis via API:** The combined output (data quality report, type-correction suggestions, and AI-generated metadata) will be made available through a FastAPI endpoint.  
* **5.3.2. Receive User Updates:** A second API endpoint will accept a JSON payload from the user containing the final, corrected version of the metadata.  
* **5.3.3. Persistent Storage:**  
  * Upon receiving the final version, the system will save the metadata.  
  * The metadata for each dataset should be stored in a structured format (e.g., a JSON file named {dataset\_name}\_metadata.json) in a designated metadata directory. This file will serve as the memory for future interactions with this dataset.

### **6\. API Endpoints (FastAPI)**

* **POST /v1/analyze**  
  * **Description:** Kicks off the analysis for a specified dataset.  
  * **Request Body:**  
    {  
      "file\_path": "dataset/logistics\_data\_q1.csv"  
    }

  * **Success Response (200 OK):**  
    {  
      "dataset\_name": "logistics\_data\_q1.csv",  
      "initial\_analysis": {  
        "size": { "rows": 10000, "columns": 16 },  
        "data\_quality\_report": {  
          "missing\_values": \[  
            { "column\_name": "Delay\_min", "missing\_count": 520, "missing\_percentage": 5.2 },  
            { "column\_name": "CustomerRating", "missing\_count": 150, "missing\_percentage": 1.5 }  
          \],  
          "type\_correction\_suggestions": \[  
            { "column\_name": "Duration\_min", "current\_type": "object", "suggested\_type": "numerical" }  
          \],  
          "statistics": {  
            // Output of pandas.describe() converted to JSON  
          }  
        }  
      },  
      "generated\_metadata": {  
        // The full metadata object generated by the AI agent (see section 7.1)  
      }  
    }

  * **Error Response (404 Not Found):** If file\_path does not exist.  
  * **Error Response (500 Internal Server Error):** For processing failures.  
* **POST /v1/metadata/finalize**  
  * **Description:** Saves the user-corrected and finalized metadata.  
  * **Request Body:**  
    {  
      "dataset\_name": "logistics\_data\_q1.csv",  
      "final\_metadata": {  
        // The full metadata object, as corrected by the user  
      }  
    }

  * **Success Response (200 OK):**  
    {  
      "status": "success",  
      "message": "Metadata for logistics\_data\_q1.csv has been saved.",  
      "file\_path": "metadata/logistics\_data\_q1\_metadata.json"  
    }

  * **Error Response (400 Bad Request):** If the request body is malformed.

### **7\. Agent & Prompt Design**

* **7.1. Agent Persona (System Prompt):**You are a world-class Senior Transportation Logistics Analyst with 20 years of experience. Your expertise lies in quickly understanding complex logistics datasets. You are meticulous, detail-oriented, and your goal is to create clear, unambiguous, and structured metadata for a new dataset. You think step-by-step to deconstruct column names, infer their business meaning, and classify them correctly.  
* **7.2. Metadata Generation Prompt (User Prompt for the LLM):Objective:** Analyze the provided dataset schema and sample data to generate a comprehensive metadata JSON object.**Your Persona:** Senior Transportation Logistics Analyst.**Input Data:**{  
    "columns": \["City", "ServiceType", "Distance\_km", "OnTimeDelivery", "Duration\_min"\],  
    "column\_data\_types": {  
      "City": "object",  
      "ServiceType": "object",  
      "Distance\_km": "float64",  
      "OnTimeDelivery": "int64",  
      "Duration\_min": "object"  
    },  
    "categorical\_unique\_values": {  
      "ServiceType": \["2W", "3W", "EV", "LCV"\]  
    },  
    "data\_sample": \[  
      // CSV rows as a list of lists or list of dicts  
    \]  
  }  
  **Instructions:**  
  1. Write a brief, high-level dataset\_description explaining what the dataset likely represents.  
  2. Iterate through each column provided in the columns list.  
  3. For each column, create a JSON object with the following keys:  
     * column\_name: The exact name of the column.  
     * description: A clear, business-friendly description. Example: For Distance\_km, describe it as "The total distance of the trip in kilometers."  
     * data\_type: Classify the column into one of these specific types: 'Numerical', 'Categorical', 'Datetime', 'ID', 'Text', 'Boolean'. Be smart about this; a column like OnTimeDelivery with values 0 and 1 is 'Boolean'. Duration\_min with string numbers is 'Numerical'.  
     * categorical\_values: If and only if the data\_type is 'Categorical', this key must be present. It should be an array of objects, where you provide a value and a description for each unique value provided in the input. Example: For ServiceType value 2W, the description should be "2 Wheeler Vehicle".

Output Format:  
You MUST respond with a single, valid JSON object. Do not include any text or explanations outside of the JSON structure.{  
  "dataset\_description": "A brief summary here.",  
  "columns": \[  
    {  
      "column\_name": "City",  
      "description": "The city where the delivery took place.",  
      "data\_type": "Categorical",  
      "categorical\_values": \[  
        // Descriptions for unique cities if applicable, or this key can be omitted if too many unique values  
      \]  
    },  
    // ... other column objects  
  \]  
}

### **8\. Data Schemas**

#### **8.1. Final Metadata Schema ({dataset\_name}\_metadata.json)**

This is the canonical structure for the stored metadata.

{  
  "dataset\_name": "string",  
  "dataset\_description": "string",  
  "columns": \[  
    {  
      "column\_name": "string",  
      "description": "string",  
      "data\_type": "string" // 'Numerical', 'Categorical', 'Datetime', etc.  
      "categorical\_values": \[  
        {  
          "value": "string",  
          "description": "string"  
        }  
      \] // Optional: Only for categorical types  
    }  
  \]  
}

### **9\. Technology Stack**

* **Backend Language:** Python 3.10+  
* **Web Framework:** FastAPI  
* **Data Manipulation:** Pandas  
* **Agent/LLM Orchestration:** LangChain, LangGraph  
* **API Testing:** Swagger UI (auto-generated by FastAPI), Postman

### **10\. Out of Scope for Phase 1**

* **User Interface (UI):** All interactions will be via API. No frontend will be built.  
* **Advanced Analytics:** This phase focuses only on profiling and metadata. No querying, charting, or complex analysis will be implemented.  
* **Database Integration:** Metadata will be stored as JSON files. A more robust database solution (like PostgreSQL or a vector database) is deferred.  
* **User Authentication:** The API endpoints will be open initially.  
* **Applying Data Type Corrections:** The system will only *suggest* corrections; it will not automatically apply them to the dataset in this phase.  
* **Cloud Deployment:** The service will be designed to run locally.

