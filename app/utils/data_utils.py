"""Data processing utilities."""

import pandas as pd
from typing import Any, Dict, List


def convert_to_json_serializable(obj: Any) -> Any:
    """Convert pandas/numpy objects to JSON-serializable Python types."""
    if obj is None or pd.isna(obj):
        return None
    elif hasattr(obj, 'item'):  # numpy scalar
        return obj.item()
    elif isinstance(obj, (list, tuple)):
        return [convert_to_json_serializable(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_to_json_serializable(value) for key, value in obj.items()}
    else:
        return obj


def safe_describe_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    """Generate DataFrame description with JSON-safe values."""
    desc = df.describe(include="all")
    
    # Replace NaN/NaT with None for JSON compatibility
    desc = desc.where(pd.notnull(desc), None)
    
    # Convert to Python native types more safely
    description = {}
    for col_name, col_data in desc.to_dict().items():
        description[col_name] = {}
        for stat_name, stat_value in col_data.items():
            description[col_name][stat_name] = convert_to_json_serializable(stat_value)
    
    return description


def get_categorical_unique_values(df: pd.DataFrame, max_unique: int = None) -> Dict[str, List[Any]]:
    """Extract unique values for categorical columns."""
    if max_unique is None:
        from ..config.settings import get_settings
        max_unique = get_settings().max_categorical_unique

    categorical_values: Dict[str, List[Any]] = {}
    for column_name, dtype in df.dtypes.items():
        if str(dtype) in {"object", "category"}:
            unique_vals = pd.unique(df[column_name].dropna())
            if len(unique_vals) <= max_unique:
                # Convert to native Python types for JSON serialization
                categorical_values[column_name] = [
                    convert_to_json_serializable(val) for val in unique_vals
                ]
    return categorical_values


def get_data_sample(df: pd.DataFrame, sample_size: int = None) -> List[Dict[str, Any]]:
    """Get a sample of data rows as JSON-serializable dictionaries."""
    if sample_size is None:
        from ..config.settings import get_settings
        sample_size = get_settings().data_sample_size

    sample_df = df.head(sample_size).where(pd.notnull(df.head(sample_size)), None)
    return [
        {key: convert_to_json_serializable(value) for key, value in row.items()}
        for row in sample_df.to_dict(orient="records")
    ]


def get_missing_values_report(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Generate missing values report for all columns."""
    report: List[Dict[str, Any]] = []
    total_rows = len(df)
    for column_name in df.columns:
        missing_count = int(df[column_name].isna().sum())
        missing_percentage = (missing_count / total_rows * 100.0) if total_rows else 0.0
        report.append(
            {
                "column_name": column_name,
                "missing_count": missing_count,
                "missing_percentage": round(missing_percentage, 4),
            }
        )
    return report

def filter_required_columns(metadata_dict, filtered_columns):
    """
    Filters the metadata dictionary to return only columns where required = 'true'.
    
    Args:
        metadata_dict (dict): The metadata dictionary containing:
            - dataset_description (str): Brief description of the dataset
            - columns (list): List of column metadata objects
    
    Returns:
        dict: A new dictionary with the same structure but only containing
              columns where required = 'true'
    """
    if not isinstance(metadata_dict, dict):
        raise ValueError("Input must be a dictionary")
    
    if 'columns' not in metadata_dict:
        raise ValueError("Input dictionary must contain a 'columns' key")
    
    
    
    # Create new dictionary with filtered columns
    filtered_dict = {
        'dataset_description': metadata_dict.get('dataset_description', ''),
        'columns': filtered_columns
    }
    
    return filtered_dict