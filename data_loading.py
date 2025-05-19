import os
from typing import Dict, Any, Optional, List
import pandas as pd
from app.utils.exceptions import ToolExecutionError, FileProcessingError


def load_data_serializable(data: List[Dict[str, Any]], metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Loads data from a list of dictionaries into a pandas DataFrame.
    
    Args:
        data: List of dictionaries where each dictionary represents a row
        metadata: Optional metadata about the data source
        
    Returns:
        Dictionary containing the loaded DataFrame and metadata
    """
    try:
        # Create DataFrame from the list of dictionaries
        df = pd.DataFrame(data)
        
        # If no data provided, return an empty DataFrame with appropriate message
        if not data:
            return {
                'result_df': df,
                'message': "Empty data provided. Created an empty DataFrame.",
                'metadata': metadata or {
                    'rows': 0,
                    'columns': 0,
                    'column_names': [],
                    'has_missing_values': False,
                    'missing_value_counts': {}
                }
            }
        
        # Basic data cleaning and preparation
        # 1. Remove leading/trailing spaces from column names
        df.columns = df.columns.str.strip()
        
        # 2. Attempt to convert numeric columns stored as strings
        for col in df.select_dtypes(include=['object']).columns:
            try:
                # Try to convert to numeric, but only if it doesn't introduce NaNs
                numeric_series = pd.to_numeric(df[col], errors='coerce')
                # If no NaNs were introduced, or the NaNs were already there, convert
                if numeric_series.isna().sum() == df[col].isna().sum():
                    df[col] = numeric_series
            except:
                # If any error occurs, keep the column as is
                pass
        
        # Use provided metadata or generate default metadata
        if metadata is None:
            metadata = {}
        
        # Ensure required metadata fields exist
        metadata.update({
            'rows': len(df),
            'columns': len(df.columns),
            'column_names': df.columns.tolist(),
            'column_dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()},
            'has_missing_values': df.isna().any().any(),
            'missing_value_counts': df.isna().sum().to_dict()
        })
        
        # Prepare result with metadata
        result = {
            'result_df': df,
            'message': f"Data loaded successfully with {len(df)} rows and {len(df.columns)} columns.",
            'metadata': metadata
        }
        
        return result
    
    except Exception as e:
        # Wrap other exceptions
        raise ToolExecutionError(
            "load_data_serializable", 
            f"Error loading data: {str(e)}"
        ) 