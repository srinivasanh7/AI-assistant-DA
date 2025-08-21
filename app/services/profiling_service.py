"""Comprehensive data profiling service with type conversion analysis."""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Tuple

import pandas as pd

from ..config.settings import get_settings
from ..models.schemas import AgentInput
from ..utils.data_utils import (
    convert_to_json_serializable,
    get_categorical_unique_values,
    get_data_sample,
    get_missing_values_report,
    safe_describe_dataframe,
)


class ProfilingService:
    """Service for comprehensive dataset profiling and type analysis."""

    def __init__(self, settings=None):
        """Initialize profiling service with settings."""
        self.settings = settings or get_settings()
        self.numeric_threshold = self.settings.numeric_threshold
        self.datetime_threshold = self.settings.datetime_threshold
        self.categorical_threshold = self.settings.categorical_threshold

    def profile_dataset(self, file_path: str) -> Tuple[Dict[str, Any], AgentInput]:
        """
        Perform comprehensive dataset profiling.
        
        Returns:
            Tuple of (initial_analysis, agent_input)
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(file_path)

        print(f"  📋 Loading CSV file...")
        csv_start = time.time()
        df = pd.read_csv(file_path)
        csv_time = time.time() - csv_start
        print(f"  📋 CSV loaded in {csv_time:.3f}s - Shape: {df.shape}")
        
        # Basic dataset information
        size = {"rows": int(df.shape[0]), "columns": int(df.shape[1])}
        
        # Generate comprehensive analysis
        print(f"  🔍 Analyzing missing values...")
        missing_start = time.time()
        missing_values = get_missing_values_report(df)
        missing_time = time.time() - missing_start
        print(f"  🔍 Missing values analysis completed in {missing_time:.3f}s")
        
        print(f"  🔧 Inferring type corrections...")
        type_start = time.time()
        type_corrections = self._infer_type_corrections(df)
        type_time = time.time() - type_start
        print(f"  🔧 Type corrections analysis completed in {type_time:.3f}s")
        
        print(f"  📊 Generating statistics...")
        stats_start = time.time()
        statistics = safe_describe_dataframe(df)
        stats_time = time.time() - stats_start
        print(f"  📊 Statistics generated in {stats_time:.3f}s")
        
        # Prepare agent input
        print(f"  🎯 Preparing agent input...")
        agent_prep_start = time.time()
        columns = [str(c) for c in df.columns.tolist()]
        column_data_types = {str(col): str(dtype) for col, dtype in df.dtypes.items()}
        categorical_values = get_categorical_unique_values(df)
        data_sample = get_data_sample(df)
        agent_prep_time = time.time() - agent_prep_start
        print(f"  🎯 Agent input prepared in {agent_prep_time:.3f}s")
        
        initial_analysis = {
            "size": size,
            "data_quality_report": {
                "missing_values": missing_values,
                "type_correction_suggestions": type_corrections,
                "statistics": statistics,
            },
        }
        
        agent_input = AgentInput(
            columns=columns,
            column_data_types=column_data_types,
            categorical_unique_values=categorical_values,
            data_sample=data_sample,
        )
        
        return initial_analysis, agent_input

    def analyze_column_types(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Comprehensive column type analysis with correction suggestions.
        
        Returns:
            Dictionary containing analysis results and suggestions
        """
        results = {
            'column_analysis': [],
            'type_suggestions': [],
            'summary': {}
        }
        
        for column_name in df.columns:
            column_info = self._analyze_single_column(df[column_name], column_name)
            results['column_analysis'].append(column_info)
            
            # Add to suggestions if correction is recommended
            if column_info.get('suggested_type') != column_info.get('current_type'):
                results['type_suggestions'].append({
                    'column_name': column_name,
                    'current_type': column_info['current_type'],
                    'suggested_type': column_info['suggested_type'],
                    'confidence': column_info['confidence'],
                    'reason': column_info['reason'],
                    'sample_values': column_info['sample_values'],
                    'sample_converted': column_info.get('sample_converted', [])
                })
        
        # Generate summary
        results['summary'] = self._generate_summary(results['column_analysis'])
        
        return results

    def _analyze_single_column(self, series: pd.Series, column_name: str) -> Dict[str, Any]:
        """Analyze a single column for type suggestions."""
        column_info = {
            'column_name': column_name,
            'current_type': str(series.dtype),
            'suggested_type': str(series.dtype),
            'null_count': int(series.isnull().sum()),
            'null_percentage': float(series.isnull().sum() / len(series) * 100),
            'unique_count': int(series.nunique()),
            'unique_percentage': float(series.nunique() / len(series) * 100),
            'sample_values': [],
            'confidence': 0.0,
            'reason': 'No conversion needed'
        }
        
        # Get sample values (non-null)
        non_null = series.dropna()
        if not non_null.empty:
            sample_size = min(5, len(non_null))
            column_info['sample_values'] = [
                convert_to_json_serializable(val) for val in non_null.head(sample_size).tolist()
            ]
        
        # Skip analysis if mostly null
        if len(non_null) < 3:
            column_info['reason'] = 'Insufficient non-null data'
            return column_info
        
        # Only analyze object/string columns for conversions
        if str(series.dtype) == 'object':
            # Check for numeric conversion
            numeric_result = self._check_numeric_conversion(non_null)
            if numeric_result['convertible_ratio'] >= self.numeric_threshold:
                column_info.update({
                    'suggested_type': 'numeric',
                    'confidence': numeric_result['convertible_ratio'],
                    'reason': f"Can convert {numeric_result['convertible_ratio']:.1%} of values to numeric",
                    'sample_converted': numeric_result['sample_converted']
                })
                return column_info

            # Check for datetime conversion
            datetime_result = self._check_datetime_conversion(non_null)
            if datetime_result['convertible_ratio'] >= self.datetime_threshold:
                column_info.update({
                    'suggested_type': 'datetime',
                    'confidence': datetime_result['convertible_ratio'],
                    'reason': f"Can convert {datetime_result['convertible_ratio']:.1%} of values to datetime",
                    'sample_converted': datetime_result['sample_converted']
                })
                return column_info

            # Check for boolean conversion
            boolean_result = self._check_boolean_conversion(non_null)
            if boolean_result['is_boolean']:
                column_info.update({
                    'suggested_type': 'boolean',
                    'confidence': 1.0,
                    'reason': f"Contains boolean-like values: {boolean_result['unique_values']}",
                    'sample_converted': boolean_result['sample_converted']
                })
                return column_info

        # Check if should be categorical
        if (column_info['unique_count'] <= self.categorical_threshold and
            column_info['unique_percentage'] < 50 and
            str(series.dtype) in ['object', 'int64', 'float64']):

            column_info.update({
                'suggested_type': 'categorical',
                'confidence': 1.0 - (column_info['unique_percentage'] / 100),
                'reason': f"Low cardinality: {column_info['unique_count']} unique values ({column_info['unique_percentage']:.1f}%)"
            })

        return column_info

    def _infer_type_corrections(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Suggest column type corrections using comprehensive analysis."""
        print(f"    🔍 Analyzing {len(df.columns)} columns for type corrections...")
        suggestions: List[Dict[str, Any]] = []
        for i, column_name in enumerate(df.columns, 1):
            if i % 10 == 0 or i == len(df.columns):
                print(f"    🔍 Processed {i}/{len(df.columns)} columns...")
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
                suggestion["sample_values"] = [
                    convert_to_json_serializable(val) for val in non_null.head(sample_size).tolist()
                ]

            # Skip if very sparse
            if len(non_null) < 3:
                suggestion["reason"] = "Insufficient non-null data"
            else:
                # For object types, test numeric/datetime/boolean first
                if current_type == "object":
                    numeric_result = self._check_numeric_conversion(non_null)
                    if numeric_result["convertible_ratio"] >= self.numeric_threshold:
                        suggestion.update(
                            {
                                "suggested_type": "numeric",
                                "confidence": numeric_result["convertible_ratio"],
                                "reason": f"Can convert {numeric_result['convertible_ratio']:.1%} of values to numeric",
                                "sample_converted": numeric_result["sample_converted"],
                            }
                        )
                    else:
                        datetime_result = self._check_datetime_conversion(non_null)
                        if datetime_result["convertible_ratio"] >= self.datetime_threshold:
                            suggestion.update(
                                {
                                    "suggested_type": "datetime",
                                    "confidence": datetime_result["convertible_ratio"],
                                    "reason": f"Can convert {datetime_result['convertible_ratio']:.1%} of values to datetime",
                                    "sample_converted": datetime_result["sample_converted"],
                                }
                            )
                        else:
                            boolean_result = self._check_boolean_conversion(non_null)
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
                    unique_count <= self.categorical_threshold
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

        return suggestions

    def _check_numeric_conversion(self, series: pd.Series) -> Dict[str, Any]:
        """Check if series can be converted to numeric."""
        result = {"convertible_ratio": 0.0, "sample_converted": []}
        try:
            converted = pd.to_numeric(series, errors="coerce")
            convertible_count = converted.notna().sum()
            result["convertible_ratio"] = convertible_count / len(series) if len(series) else 0.0
            if convertible_count > 0:
                valid_converted = converted.dropna()
                sample_size = min(3, len(valid_converted))
                result["sample_converted"] = [
                    convert_to_json_serializable(val) for val in valid_converted.head(sample_size).tolist()
                ]
        except Exception:
            pass
        return result

    def _check_datetime_conversion(self, series: pd.Series) -> Dict[str, Any]:
        """Check if series can be converted to datetime."""
        result = {"convertible_ratio": 0.0, "sample_converted": []}
        try:
            converted = pd.to_datetime(series, errors="coerce")
            convertible_count = converted.notna().sum()
            result["convertible_ratio"] = convertible_count / len(series) if len(series) else 0.0
            if convertible_count > 0:
                valid_converted = converted.dropna()
                sample_size = min(3, len(valid_converted))
                result["sample_converted"] = [
                    str(val) for val in valid_converted.head(sample_size).tolist()
                ]
        except Exception:
            pass
        return result

    def _check_boolean_conversion(self, series: pd.Series) -> Dict[str, Any]:
        """Check if series contains boolean-like values."""
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

    def _generate_summary(self, column_analysis: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics."""
        total_columns = len(column_analysis)

        type_counts = {}
        suggested_type_counts = {}

        for col in column_analysis:
            current_type = col['current_type']
            suggested_type = col['suggested_type']

            type_counts[current_type] = type_counts.get(current_type, 0) + 1
            suggested_type_counts[suggested_type] = suggested_type_counts.get(suggested_type, 0) + 1

        suggestions_count = sum(1 for col in column_analysis
                               if col['suggested_type'] != col['current_type'])

        return {
            'total_columns': total_columns,
            'suggestions_count': suggestions_count,
            'current_type_distribution': type_counts,
            'suggested_type_distribution': suggested_type_counts,
            'conversion_rate': suggestions_count / total_columns if total_columns > 0 else 0
        }

    def print_analysis_results(self, results: Dict[str, Any]) -> None:
        """Pretty print the analysis results."""
        print("=" * 60)
        print("DATA TYPE ANALYSIS RESULTS")
        print("=" * 60)

        print(f"\nSUMMARY:")
        print(f"Total columns: {results['summary']['total_columns']}")
        print(f"Columns needing conversion: {results['summary']['suggestions_count']}")
        print(f"Conversion rate: {results['summary']['conversion_rate']:.1%}")

        if results['type_suggestions']:
            print(f"\nTYPE CONVERSION SUGGESTIONS:")
            print("-" * 60)

            for suggestion in results['type_suggestions']:
                print(f"\nColumn: {suggestion['column_name']}")
                print(f"Current type: {suggestion['current_type']}")
                print(f"Suggested type: {suggestion['suggested_type']}")
                print(f"Confidence: {suggestion['confidence']:.1%}")
                print(f"Reason: {suggestion['reason']}")
                print(f"Sample values: {suggestion['sample_values']}")
                if suggestion.get('sample_converted'):
                    print(f"Sample converted: {suggestion['sample_converted']}")
        else:
            print("\nNo type conversion suggestions found.")
            
            # Check for datetime conversion
            datetime_result = self._check_datetime_conversion(non_null)
            if datetime_result['convertible_ratio'] >= self.datetime_threshold:
                column_info.update({
                    'suggested_type': 'datetime',
                    'confidence': datetime_result['convertible_ratio'],
                    'reason': f"Can convert {datetime_result['convertible_ratio']:.1%} of values to datetime",
                    'sample_converted': datetime_result['sample_converted']
                })
                return column_info
            
            # Check for boolean conversion
            boolean_result = self._check_boolean_conversion(non_null)
            if boolean_result['is_boolean']:
                column_info.update({
                    'suggested_type': 'boolean',
                    'confidence': 1.0,
                    'reason': f"Contains boolean-like values: {boolean_result['unique_values']}",
                    'sample_converted': boolean_result['sample_converted']
                })
                return column_info
        
        # Check if should be categorical
        if (column_info['unique_count'] <= self.categorical_threshold and 
            column_info['unique_percentage'] < 50 and
            str(series.dtype) in ['object', 'int64', 'float64']):
            
            column_info.update({
                'suggested_type': 'categorical',
                'confidence': 1.0 - (column_info['unique_percentage'] / 100),
                'reason': f"Low cardinality: {column_info['unique_count']} unique values ({column_info['unique_percentage']:.1f}%)"
            })
        
        return column_info
