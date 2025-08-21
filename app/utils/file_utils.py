"""File handling utilities."""

import json
import os
from typing import Any, Dict, List
import time


def ensure_directory_exists(directory_path: str) -> None:
    """Ensure that a directory exists, creating it if necessary."""
    os.makedirs(directory_path, exist_ok=True)


def save_json_file(data: Dict[str, Any], file_path: str) -> None:
    """Save data to a JSON file with proper formatting."""
    ensure_directory_exists(os.path.dirname(file_path))
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_json_file(file_path: str) -> Dict[str, Any]:
    """Load data from a JSON file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def file_exists(file_path: str) -> bool:
    """Check if a file exists."""
    return os.path.exists(file_path)


def get_filename_without_extension(file_path: str) -> str:
    """Get filename without extension from a file path."""
    return os.path.splitext(os.path.basename(file_path))[0]


def get_metadata_file_path(dataset_name: str, metadata_dir: str = "metadata") -> str:
    """Generate metadata file path for a dataset, handling timestamped files."""
    import glob
    
    # First try the exact filename
    exact_path = os.path.join(metadata_dir, f"{dataset_name}_metadata.json")
    if os.path.exists(exact_path):
        return exact_path
    
    # If not found, try to find timestamped versions
    # Remove .csv extension if present to search for timestamped versions
    base_name = dataset_name.replace('.csv', '')
    pattern = os.path.join(metadata_dir, f"*{base_name}.csv_metadata.json")
    matches = glob.glob(pattern)
    
    if matches:
        # Return the most recent one (sorted by filename which includes timestamp)
        most_recent = sorted(matches)[-1]
        print(f"🔍 Mapped {dataset_name} to timestamped file: {os.path.basename(most_recent)}")
        return most_recent
    
    # If no matches found, return the original path (will cause 404)
    return exact_path


def find_dataset_file(dataset_name: str, datasets_dir: str = "datasets", uploads_dir: str = "uploads") -> str:
    """Find the actual dataset file, handling timestamped versions."""
    import glob
    
    # Check datasets directory first
    exact_datasets_path = os.path.join(datasets_dir, dataset_name)
    if os.path.exists(exact_datasets_path):
        return exact_datasets_path
    
    # Check uploads directory
    exact_uploads_path = os.path.join(uploads_dir, dataset_name)  
    if os.path.exists(exact_uploads_path):
        return exact_uploads_path
    
    # Try to find timestamped versions in uploads directory
    base_name = dataset_name.replace('.csv', '')
    uploads_pattern = os.path.join(uploads_dir, f"*{base_name}.csv")
    uploads_matches = glob.glob(uploads_pattern)
    
    if uploads_matches:
        most_recent = sorted(uploads_matches)[-1]
        print(f"🔍 Mapped {dataset_name} to timestamped dataset: {os.path.basename(most_recent)}")
        return most_recent
    
    # Try timestamped versions in datasets directory  
    datasets_pattern = os.path.join(datasets_dir, f"*{base_name}.csv")
    datasets_matches = glob.glob(datasets_pattern)
    
    if datasets_matches:
        most_recent = sorted(datasets_matches)[-1]
        print(f"🔍 Mapped {dataset_name} to timestamped dataset: {os.path.basename(most_recent)}")
        return most_recent
    
    # If nothing found, raise an error
    raise FileNotFoundError(f"Dataset not found: {dataset_name} (checked {datasets_dir} and {uploads_dir})")

def get_relationships_file_path(dataset_name: str, metadata_dir: str = "metadata") -> str:
    """Generate relationships file path for a dataset."""
    return os.path.join(metadata_dir, f"{dataset_name}_relationships.json")

def convert_csv_to_parquet(
    dataset_name: str, 
    filtered_columns: List[str],
    datasets_dir: str = "datasets",
    temp_dir: str = "temp_data",
    uploads_subdir: str = "uploads"
) -> str:
    """
    Convert a CSV dataset to parquet format with only specified columns.
    
    Args:
        dataset_name (str): Name of the dataset file to find and convert
        filtered_columns (List[str]): List of column names to include in the parquet file
        datasets_dir (str): Base directory where datasets are stored
        output_dir (str): Directory where the parquet file will be saved
        session_id (Optional[str]): Session ID for naming the output file. If None, uses dataset_name
        uploads_subdir (str): Subdirectory within datasets_dir to search (default: "uploads")
        
    Returns:
        str: Path to the saved parquet file
        
    Raises:
        FileNotFoundError: If dataset file cannot be found
        ValueError: If filtered columns are not found in the dataset
        Exception: For any other errors during conversion
    """
    try:
        import pandas as pd
        # Find dataset file using smart lookup
        final_dataset_path = find_dataset_file(dataset_name, datasets_dir, uploads_subdir)
        print(f"📁 Found dataset: {final_dataset_path}")
        # Load CSV with timing
        print(f"📊 Loading dataset from: {final_dataset_path}")
        start_time = time.time()
        df = pd.read_csv(final_dataset_path)
        load_time = time.time() - start_time
        print(f"✅ CSV loaded in {load_time:.2f}s ({len(df)} rows, {len(df.columns)} columns)")
        
        # Filter columns if specified
        if filtered_columns:
            # Check if all filtered columns exist in the dataset
            missing_columns = set(filtered_columns) - set(df.columns)
            if missing_columns:
                raise ValueError(f"The following columns are not found in the dataset: {missing_columns}")
            
            # Select only the filtered columns
            df_filtered = df[filtered_columns]
            print(f"🔍 Filtered to {len(filtered_columns)} columns: {filtered_columns}")
        else:
            df_filtered = df
            print("ℹ️  No column filtering applied - using all columns")
        

        # Use dataset name without extension
        base_name = os.path.splitext(os.path.basename(dataset_name))[0]
        output_filename = f"{base_name}_filtered.parquet"
        
        # Ensure output directory exists
        os.makedirs(temp_dir, exist_ok=True)
        
        # Save as parquet
        parquet_path = os.path.join(temp_dir, output_filename)
        start_save_time = time.time()
        df_filtered.to_parquet(parquet_path, index=False)
        save_time = time.time() - start_save_time
        
        print(f"💾 Dataset saved as parquet: {parquet_path}")
        print(f"⚡ Parquet saved in {save_time:.2f}s ({len(df_filtered)} rows, {len(df_filtered.columns)} columns)")
        
    except FileNotFoundError as e:
        print(f"❌ Dataset file not found: {e}")
        raise
    except ValueError as e:
        print(f"❌ Column filtering error: {e}")
        raise
    except Exception as e:
        print(f"❌ Failed to convert CSV to parquet: {e}")
        raise
