import pandas as pd
from typing import List, Dict, Any, Union
from app.utils.exceptions import ToolExecutionError


def filter_data_serializable(data: List[Dict[str, Any]], filter_criteria: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Filters data based on multiple criteria.

    Args:
        data: List of dictionaries where each dictionary represents a row
        filter_criteria: A list of dictionaries, where each dictionary
                         specifies a column, operator (==, >, <, >=, <=, !=),
                         and value for filtering.
                         Example: [{'column': 'Sales', 'operator': '>', 'value': 1000}]

    Returns:
        Dictionary containing the filtered data and metadata about the operation.
    """
    # Input validation
    if not isinstance(data, list):
        raise ToolExecutionError("filter_data_serializable", "Data must be a list of dictionaries")

    if not isinstance(filter_criteria, list):
        raise ToolExecutionError(
            "filter_data_serializable", 
            f"filter_criteria must be a list, got {type(filter_criteria).__name__}"
        )
    
    # Convert to DataFrame for efficient filtering
    df = pd.DataFrame(data)
    original_row_count = len(df)
    
    # If the DataFrame is empty, return early
    if len(df) == 0:
        return {
            'result_df': df,
            'result_data': [],
            'message': "No data to filter.",
            'metadata': {
                'original_rows': 0,
                'filtered_rows': 0,
                'rows_removed': 0,
                'percentage_removed': 0,
                'filter_criteria': filter_criteria,
                'filter_steps': []
            }
        }
    
    # Keep track of how many rows were filtered at each step
    filter_steps = []
    
    try:
        for i, criterion in enumerate(filter_criteria):
            # Validate criterion structure
            if not isinstance(criterion, dict):
                raise ToolExecutionError(
                    "filter_data_serializable", 
                    f"Each filter criterion must be a dictionary, got {type(criterion).__name__}"
                )
            
            required_keys = ['column', 'operator', 'value']
            for key in required_keys:
                if key not in criterion:
                    raise ToolExecutionError(
                        "filter_data_serializable", 
                        f"Filter criterion missing required key: '{key}'"
                    )
            
            col = criterion['column']
            op = criterion['operator']
            val = criterion['value']
            
            # Validate column exists
            if col not in df.columns:
                raise ToolExecutionError(
                    "filter_data_serializable", 
                    f"Column '{col}' not found in data. Available columns: {', '.join(df.columns)}"
                )
            
            # Apply filter based on operator
            pre_filter_count = len(df)
            
            if op == '==':
                df = df[df[col] == val]
            elif op == '>':
                df = df[df[col] > val]
            elif op == '<':
                df = df[df[col] < val]
            elif op == '>=':
                df = df[df[col] >= val]
            elif op == '<=':
                df = df[df[col] <= val]
            elif op == '!=':
                df = df[df[col] != val]
            else:
                raise ToolExecutionError(
                    "filter_data_serializable", 
                    f"Unsupported operator: '{op}'. Supported operators: ==, >, <, >=, <=, !="
                )
            
            # Track how many rows were filtered in this step
            post_filter_count = len(df)
            rows_filtered = pre_filter_count - post_filter_count
            
            filter_steps.append({
                'step': i + 1,
                'column': col,
                'operator': op,
                'value': val,
                'rows_before': pre_filter_count,
                'rows_after': post_filter_count,
                'rows_filtered': rows_filtered,
                'percentage_filtered': round((rows_filtered / pre_filter_count * 100), 2) if pre_filter_count > 0 else 0
            })
        
        # Convert filtered DataFrame back to a list of dictionaries
        result_data = df.to_dict(orient='records')
        
        # Prepare result with metadata
        result = {
            'result_df': df,  # Include DataFrame for compatibility
            'result_data': result_data,  # Include serializable list of dicts
            'message': f"Data filtered successfully. {original_row_count - len(df)} rows were filtered out.",
            'metadata': {
                'original_rows': original_row_count,
                'filtered_rows': len(df),
                'rows_removed': original_row_count - len(df),
                'percentage_removed': round(((original_row_count - len(df)) / original_row_count * 100), 2) if original_row_count > 0 else 0,
                'filter_criteria': filter_criteria,
                'filter_steps': filter_steps
            }
        }
        
        return result
        
    except Exception as e:
        # If it's already a ToolExecutionError, re-raise it
        if isinstance(e, ToolExecutionError):
            raise e
            
        # Otherwise wrap it
        raise ToolExecutionError("filter_data_serializable", str(e)) 