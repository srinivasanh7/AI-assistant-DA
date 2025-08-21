# Postman Testing Guide for Enhanced /v1/analyze Endpoint

## Overview
The `/v1/analyze` endpoint now supports both file path and file upload methods. The endpoint automatically detects the content type and handles the request accordingly.

## Method 1: File Path (Existing)

### Request
- **Method**: POST
- **URL**: `http://localhost:8000/v1/analyze`
- **Headers**: 
  ```
  Content-Type: application/json
  ```
- **Body** (raw JSON):
  ```json
  {
    "file_path": "datasets/logistics_dataset.csv"
  }
  ```

## Method 2: File Upload (New)

### Request
- **Method**: POST
- **URL**: `http://localhost:8000/v1/analyze`
- **Headers**: (Don't set Content-Type, let Postman handle it)
- **Body** (form-data):
  - Key: `uploaded_file`
  - Type: File
  - Value: Select your CSV file

## Expected Response (Both Methods)

```json
{
  "dataset_name": "logistics_dataset.csv",
  "initial_analysis": {
    "size": {
      "rows": 5000,
      "columns": 13
    },
    "data_quality_report": {
      "missing_values": [...],
      "type_correction_suggestions": [...],
      "statistics": {...}
    }
  },
  "generated_metadata": {
    "dataset_description": "...",
    "columns": [...]
  }
}
```

## Error Cases to Test

### 1. No Parameters
- **Body**: Empty or `{}`
- **Expected**: 400 Bad Request
- **Message**: "Either 'file_path' or 'uploaded_file' must be provided"

### 2. Both Parameters
- **Body**: Both file_path in form-data AND uploaded_file
- **Expected**: 400 Bad Request  
- **Message**: "Provide either 'file_path' or 'uploaded_file', not both"

### 3. Invalid File Type
- **Body**: Upload a .txt or .xlsx file
- **Expected**: 400 Bad Request
- **Message**: "Only CSV files are allowed"

### 4. File Not Found (file_path method)
- **Body**: `{"file_path": "nonexistent.csv"}`
- **Expected**: 404 Not Found
- **Message**: "File not found: nonexistent.csv"

### 5. Large File
- **Body**: Upload a file > 50MB
- **Expected**: 400 Bad Request
- **Message**: "File size too large. Maximum 50MB allowed"

## Testing Steps

1. **Start the server**: `python -m app.main`
2. **Test file path method** with existing dataset
3. **Test file upload method** with a CSV file
4. **Test error cases** to ensure proper validation
5. **Check uploads folder** to see uploaded files
6. **Verify response structure** matches expected format

## Notes

- Uploaded files are saved in the `uploads/` directory
- Filenames are prefixed with timestamp to avoid conflicts
- Only CSV files are accepted
- Maximum file size is 50MB
- Both methods produce identical response structure
