from __future__ import annotations

from typing import Any, Dict, List, Tuple
import os

import pandas as pd


def _check_numeric_conversion(series: pd.Series) -> Dict[str, Any]:
    result = {"convertible_ratio": 0.0, "sample_converted": []}
    try:
        converted = pd.to_numeric(series, errors="coerce")
        convertible_count = converted.notna().sum()
        result["convertible_ratio"] = convertible_count / len(series) if len(series) else 0.0
        if convertible_count > 0:
            valid_converted = converted.dropna()
            sample_size = min(3, len(valid_converted))
            result["sample_converted"] = valid_converted.head(sample_size).tolist()
    except Exception:
        pass
    return result


def _check_datetime_conversion(series: pd.Series) -> Dict[str, Any]:
    result = {"convertible_ratio": 0.0, "sample_converted": []}
    try:
        converted = pd.to_datetime(series, errors="coerce", infer_datetime_format=True)
        convertible_count = converted.notna().sum()
        result["convertible_ratio"] = convertible_count / len(series) if len(series) else 0.0
        if convertible_count > 0:
            valid_converted = converted.dropna()
            sample_size = min(3, len(valid_converted))
            result["sample_converted"] = valid_converted.head(sample_size).astype(str).tolist()
    except Exception:
        pass
    return result


def _check_boolean_conversion(series: pd.Series) -> Dict[str, Any]:
    result: Dict[str, Any] = {"is_boolean": False, "unique_values": [], "sample_converted": []}
    try:
        unique_lower = series.astype(str).str.lower().unique()
        unique_lower = [x for x in unique_lower if x not in ["nan", "none", ""]]
        boolean_sets = [
            {"true", "false"},
            {"yes", "no"},
            {"y", "n"},
            {"1", "0"},
            {"on", "off"},
            {"enabled", "disabled"},
            {"active", "inactive"},
        ]
        if len(unique_lower) <= 2:
            for bool_set in boolean_sets:
                if set(unique_lower).issubset(bool_set):
                    result.update(
                        {
                            "is_boolean": True,
                            "unique_values": list(unique_lower),
                            "sample_converted": [
                                True
                                if x in [
                                    "true",
                                    "yes",
                                    "y",
                                    "1",
                                    "on",
                                    "enabled",
                                    "active",
                                ]
                                else False
                                for x in unique_lower
                            ],
                        }
                    )
                    break
    except Exception:
        pass
    return result


def _infer_type_corrections(
    df: pd.DataFrame,
    numeric_threshold: float = 0.8,
    datetime_threshold: float = 0.7,
    categorical_threshold: int = 50,
) -> List[Dict[str, Any]]:
    """Suggest column type corrections using logic aligned with type_conversion.py.

    Emits suggestions only when the suggested type differs from the current dtype.
    """
    suggestions: List[Dict[str, Any]] = []
    for column_name in df.columns:
        series = df[column_name]
        current_type = str(series.dtype)

        # Build base info
        suggestion: Dict[str, Any] = {
            "column_name": column_name,
            "current_type": current_type,
            "suggested_type": current_type,
            "confidence": 0.0,
            "reason": "No conversion needed",
            "sample_values": [],
        }

        non_null = series.dropna()
        if not non_null.empty:
            sample_size = min(5, len(non_null))
            suggestion["sample_values"] = non_null.head(sample_size).tolist()

        # Skip if very sparse
        if len(non_null) < 3:
            suggestion["reason"] = "Insufficient non-null data"
        else:
            # For object types, test numeric/datetime/boolean first
            if current_type == "object":
                numeric_result = _check_numeric_conversion(non_null)
                if numeric_result["convertible_ratio"] >= numeric_threshold:
                    suggestion.update(
                        {
                            "suggested_type": "numeric",
                            "confidence": numeric_result["convertible_ratio"],
                            "reason": f"Can convert {numeric_result['convertible_ratio']:.1%} of values to numeric",
                            "sample_converted": numeric_result["sample_converted"],
                        }
                    )
                else:
                    datetime_result = _check_datetime_conversion(non_null)
                    if datetime_result["convertible_ratio"] >= datetime_threshold:
                        suggestion.update(
                            {
                                "suggested_type": "datetime",
                                "confidence": datetime_result["convertible_ratio"],
                                "reason": f"Can convert {datetime_result['convertible_ratio']:.1%} of values to datetime",
                                "sample_converted": datetime_result["sample_converted"],
                            }
                        )
                    else:
                        boolean_result = _check_boolean_conversion(non_null)
                        if boolean_result["is_boolean"]:
                            suggestion.update(
                                {
                                    "suggested_type": "boolean",
                                    "confidence": 1.0,
                                    "reason": f"Contains boolean-like values: {boolean_result['unique_values']}",
                                    "sample_converted": boolean_result["sample_converted"],
                                }
                            )

            # Consider categorical for low-cardinality across typical types
            unique_count = series.nunique(dropna=True)
            unique_percentage = (unique_count / len(series) * 100) if len(series) else 0
            if (
                unique_count <= categorical_threshold
                and unique_percentage < 50
                and current_type in ["object", "int64", "float64"]
            ):
                suggestion.update(
                    {
                        "suggested_type": "categorical",
                        "confidence": 1.0 - (unique_percentage / 100.0),
                        "reason": f"Low cardinality: {unique_count} unique values ({unique_percentage:.1f}%)",
                    }
                )

        # Emit only if change suggested
        if suggestion["suggested_type"] != suggestion["current_type"]:
            suggestions.append(suggestion)

    print("suggestion for type corrections:", suggestions)
    return suggestions


def _missing_values_report(df: pd.DataFrame) -> List[Dict[str, Any]]:
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
    print('missing values report:', report)
    return report


def _categorical_unique_values(df: pd.DataFrame) -> Dict[str, List[Any]]:
    categorical_values: Dict[str, List[Any]] = {}
    for column_name, dtype in df.dtypes.items():
        if str(dtype) in {"object", "category"}:
            unique_vals = pd.unique(df[column_name].dropna())
            if len(unique_vals) <= 50:
                # Convert to native Python types for JSON serialization
                categorical_values[column_name] = [
                    (val.item() if hasattr(val, "item") else val) for val in unique_vals
                ]
    return('categorical uniques values:', categorical_values)
    return categorical_values


def _describe_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    desc = df.describe(include="all")
    
    # Replace NaN/NaT with None for JSON compatibility
    desc = desc.where(pd.notnull(desc), None)
    
    # Convert to Python native types more safely
    description = {}
    for col_name, col_data in desc.to_dict().items():
        description[col_name] = {}
        for stat_name, stat_value in col_data.items():
            if stat_value is None:
                description[col_name][stat_name] = None
            elif pd.isna(stat_value):
                description[col_name][stat_name] = None
            else:
                # Convert numpy types to Python types
                try:
                    if hasattr(stat_value, 'item'):  # numpy scalar
                        description[col_name][stat_name] = stat_value.item()
                    else:
                        description[col_name][stat_name] = stat_value
                except (ValueError, TypeError):
                    description[col_name][stat_name] = str(stat_value)
    
    print('description:', description)
    return description


def profile_dataset(file_path: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    if not os.path.exists(file_path):
        raise FileNotFoundError(file_path)

    df = pd.read_csv(file_path)

    size = {"rows": int(df.shape[0]), "columns": int(df.shape[1])}

    missing_values = _missing_values_report(df)
    type_corrections = _infer_type_corrections(df)
    statistics = _describe_dataframe(df)

    # Base schema essentials for the agent
    columns: List[str] = [str(c) for c in df.columns.tolist()]
    column_data_types = {str(col): str(dtype) for col, dtype in df.dtypes.items()}
    categorical_values = _categorical_unique_values(df)
    data_sample = df.head(15).where(pd.notnull(df.head(15)), None).to_dict(orient="records")

    initial_analysis: Dict[str, Any] = {
        "size": size,
        "data_quality_report": {
            "missing_values": missing_values,
            "type_correction_suggestions": type_corrections,
            "statistics": statistics,
        },
    }
    print('#'*40)
    print('The inital analysis:', initial_analysis)
    agent_input: Dict[str, Any] = {
        "columns": columns,
        "column_data_types": column_data_types,
        "categorical_unique_values": categorical_values,
        "data_sample": data_sample,
    }
    print('#'*40)
    print('agent input:' , agent_input)
    return initial_analysis, agent_input

