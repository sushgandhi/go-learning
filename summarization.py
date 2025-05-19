import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Union, List
from app.utils.exceptions import ToolExecutionError
from app.utils.logging import log_info
import json


def summarize_column_serializable(data: List[Dict[str, Any]], column: str) -> Dict[str, Any]:
    """
    Provides descriptive statistics and information about a single column in the data.
    
    Args:
        data: List of dictionaries where each dictionary represents a row
        column: Name of the column to summarize
        
    Returns:
        Dictionary containing summary information about the column
    """
    try:
        # Validate inputs
        if not isinstance(data, list):
            raise ToolExecutionError("summarize_column_serializable", "Data must be a list of dictionaries")
        
        # Convert to DataFrame for processing
        df = pd.DataFrame(data)
        
        # If DataFrame is empty, return early
        if len(df) == 0:
            return {
                'result_df': pd.DataFrame(),
                'result_data': [],
                'message': "No data to summarize.",
                'metadata': {
                    'column_name': column,
                    'data_type': 'unknown',
                    'count': 0,
                    'non_null_count': 0,
                    'null_count': 0,
                    'null_percent': 0,
                    'unique_values': 0,
                    'memory_usage': 0
                }
            }
        
        # Case-insensitive column name matching
        actual_column = None
        if column in df.columns:
            actual_column = column
        else:
            # Try case-insensitive matching
            column_lower = column.lower()
            log_info(f"Trying case-insensitive match for column '{column}'", {
                "available_columns": list(df.columns),
                "lowercase_column": column_lower
            })
            for col in df.columns:
                if col.lower() == column_lower:
                    log_info(f"Found matching column: '{col}' for requested column: '{column}'")
                    actual_column = col
                    break
            
            if actual_column is None:
                log_info(f"No matching column found for '{column}'")
        
        if actual_column is None:
            raise ToolExecutionError(
                "summarize_column_serializable",
                f"Column '{column}' not found in data. Available columns: {', '.join(df.columns)}"
            )
        
        # Use the matched column name for all operations
        column = actual_column
        
        # Extract the column
        series = df[column]
        
        # Basic information
        summary = {
            'column_name': column,
            'data_type': str(series.dtype),
            'count': len(series),
            'non_null_count': series.count(),
            'null_count': series.isna().sum(),
            'null_percent': round((series.isna().sum() / len(series) * 100), 2),
            'unique_values': series.nunique(),
            'memory_usage': series.memory_usage(deep=True)
        }
        
        # Different stats based on dtype
        if pd.api.types.is_numeric_dtype(series):
            # For numeric columns
            summary['numeric_stats'] = {
                'mean': series.mean() if not all(series.isna()) else None,
                'median': series.median() if not all(series.isna()) else None,
                'std_dev': series.std() if not all(series.isna()) else None,
                'min': series.min() if not all(series.isna()) else None,
                'max': series.max() if not all(series.isna()) else None,
                'quantiles': {
                    '25%': series.quantile(0.25) if not all(series.isna()) else None,
                    '50%': series.quantile(0.50) if not all(series.isna()) else None,
                    '75%': series.quantile(0.75) if not all(series.isna()) else None,
                },
                'skew': series.skew() if not all(series.isna()) else None,
                'kurtosis': series.kurtosis() if not all(series.isna()) else None
            }
            
            # Check if column appears to be a boolean encoded as numeric
            if series.dropna().isin([0, 1]).all():
                summary['appears_boolean'] = True
                value_counts = series.value_counts().to_dict()
                summary['value_distribution'] = {
                    'count_0': value_counts.get(0, 0),
                    'count_1': value_counts.get(1, 0),
                    'percentage_0': round((value_counts.get(0, 0) / series.count() * 100), 2),
                    'percentage_1': round((value_counts.get(1, 0) / series.count() * 100), 2)
                }
            
        elif pd.api.types.is_datetime64_dtype(series):
            # For datetime columns
            summary['datetime_stats'] = {
                'min_date': series.min().strftime('%Y-%m-%d %H:%M:%S') if not all(series.isna()) else None,
                'max_date': series.max().strftime('%Y-%m-%d %H:%M:%S') if not all(series.isna()) else None,
                'range_days': (series.max() - series.min()).days if not all(series.isna()) else None
            }
            
        else:
            # For categorical/object columns
            value_counts = series.value_counts().head(10).to_dict()
            top_values_percent = sum(value_counts.values()) / series.count() * 100 if series.count() > 0 else 0
            
            summary['categorical_stats'] = {
                'top_values': value_counts,
                'top_values_percent': round(top_values_percent, 2),
                'average_string_length': round(series.astype(str).str.len().mean(), 2) if not all(series.isna()) else None
            }
            
            # Check if column appears to be a boolean
            if series.dropna().isin(['True', 'False']) or series.dropna().isin([True, False]):
                summary['appears_boolean'] = True
                bool_counts = series.value_counts().to_dict()
                summary['value_distribution'] = {
                    'count_True': bool_counts.get(True, 0) + bool_counts.get('True', 0),
                    'count_False': bool_counts.get(False, 0) + bool_counts.get('False', 0),
                    'percentage_True': round(((bool_counts.get(True, 0) + bool_counts.get('True', 0)) / series.count() * 100), 2),
                    'percentage_False': round(((bool_counts.get(False, 0) + bool_counts.get('False', 0)) / series.count() * 100), 2)
                }
                
        # Prepare DataFrame for result
        result_df = pd.DataFrame({
            'Statistic': list(summary.keys()),
            'Value': [str(v) if not isinstance(v, dict) else json.dumps(v) for v in summary.values()]
        })
        
        # Convert to serializable list of dicts
        result_data = result_df.to_dict(orient='records')
        
        # Prepare result
        result = {
            'result_df': result_df,  # Include DataFrame for compatibility
            'result_data': result_data,  # Include serializable list of dicts
            'message': f"Column '{column}' summary statistics:",
            'metadata': summary
        }
        
        return result
        
    except Exception as e:
        # If it's already a ToolExecutionError, re-raise it
        if isinstance(e, ToolExecutionError):
            raise e
            
        # Otherwise wrap it
        raise ToolExecutionError("summarize_column_serializable", str(e))


def summarize_sheet_serializable(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Provides overall statistics and information about the data.
    
    Args:
        data: List of dictionaries where each dictionary represents a row
        
    Returns:
        Dictionary containing summary information about the data
    """
    try:
        # Validate inputs
        if not isinstance(data, list):
            raise ToolExecutionError("summarize_sheet_serializable", "Data must be a list of dictionaries")
        
        # Convert to DataFrame for processing
        df = pd.DataFrame(data)
        
        # If DataFrame is empty, return early
        if len(df) == 0:
            return {
                'result_df': pd.DataFrame(),
                'result_data': [],
                'message': "No data to summarize.",
                'metadata': {
                    'shape': {'rows': 0, 'columns': 0},
                    'memory_usage_bytes': 0,
                    'columns': [],
                    'dtypes': {},
                    'null_counts': {},
                    'null_percentage': {},
                    'duplicate_rows': 0,
                    'duplicate_percentage': 0
                }
            }
        
        # Basic DataFrame info
        summary = {
            'shape': {
                'rows': len(df),
                'columns': len(df.columns)
            },
            'memory_usage_bytes': df.memory_usage(deep=True).sum(),
            'columns': df.columns.tolist(),
            'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()},
            'null_counts': df.isna().sum().to_dict(),
            'null_percentage': {col: round((null_count / len(df) * 100), 2) 
                              for col, null_count in df.isna().sum().to_dict().items()},
            'duplicate_rows': df.duplicated().sum(),
            'duplicate_percentage': round((df.duplicated().sum() / len(df) * 100), 2) if len(df) > 0 else 0
        }
        
        # Numeric column statistics
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        if numeric_cols:
            numeric_stats = df[numeric_cols].describe().to_dict()
            # Round numeric values for readability
            for col, stats in numeric_stats.items():
                numeric_stats[col] = {k: round(v, 4) if isinstance(v, (float, np.float64, np.float32)) else v 
                                     for k, v in stats.items()}
            summary['numeric_columns'] = numeric_cols
            summary['numeric_stats'] = numeric_stats
        
        # Categorical column statistics
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        if categorical_cols:
            categorical_stats = {}
            for col in categorical_cols:
                value_counts = df[col].value_counts().head(5).to_dict()
                unique_values = df[col].nunique()
                categorical_stats[col] = {
                    'unique_values': unique_values,
                    'top_5_values': value_counts,
                    'top_5_percentage': round(sum(value_counts.values()) / df[col].count() * 100, 2) if df[col].count() > 0 else 0
                }
            summary['categorical_columns'] = categorical_cols
            summary['categorical_stats'] = categorical_stats
        
        # Datetime column statistics
        datetime_cols = df.select_dtypes(include=['datetime']).columns.tolist()
        if datetime_cols:
            datetime_stats = {}
            for col in datetime_cols:
                datetime_stats[col] = {
                    'min_date': df[col].min().strftime('%Y-%m-%d %H:%M:%S') if not all(df[col].isna()) else None,
                    'max_date': df[col].max().strftime('%Y-%m-%d %H:%M:%S') if not all(df[col].isna()) else None,
                    'range_days': (df[col].max() - df[col].min()).days if not all(df[col].isna()) else None
                }
            summary['datetime_columns'] = datetime_cols
            summary['datetime_stats'] = datetime_stats
        
        # Create a DataFrame for display
        info_df = pd.DataFrame({
            'Column': df.columns.tolist(),
            'Non-Null Count': [(len(df) - df[col].isna().sum()) for col in df.columns],
            'Dtype': [str(df[col].dtype) for col in df.columns],
            'Unique Values': [df[col].nunique() for col in df.columns],
            'Memory Usage (bytes)': [df[col].memory_usage(deep=True) for col in df.columns]
        })
        
        # Convert to serializable list of dicts
        result_data = info_df.to_dict(orient='records')
        
        # Prepare result
        result = {
            'result_df': info_df,  # Include DataFrame for compatibility
            'result_data': result_data,  # Include serializable list of dicts
            'message': f"Data summary: {len(df)} rows × {len(df.columns)} columns",
            'metadata': summary
        }
        
        return result
    
    except Exception as e:
        # If it's already a ToolExecutionError, re-raise it
        if isinstance(e, ToolExecutionError):
            raise e
            
        # Otherwise wrap it
        raise ToolExecutionError("summarize_sheet_serializable", str(e)) 