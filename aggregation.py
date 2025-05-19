import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Union
from app.utils.exceptions import ToolExecutionError
from app.utils.logging import log_info


def group_and_aggregate_serializable(data: List[Dict[str, Any]], group_by_cols: List[str], agg_definitions: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Groups data by specified columns and performs aggregation operations.
    If group_by_cols is empty, performs global aggregation across the entire dataset.
    
    Args:
        data: List of dictionaries where each dictionary represents a row
        group_by_cols: List of column names to group by (can be empty for global aggregation)
        agg_definitions: List of aggregation definitions, each with column, function, and optional new_column_name
            Example: [{"column": "Sales", "function": "sum", "new_column_name": "Total Sales"}]
            
    Returns:
        Dictionary containing the aggregated data and metadata
    """
    # Input validation
    if not isinstance(data, list):
        raise ToolExecutionError("group_and_aggregate_serializable", "Data must be a list of dictionaries")
    
    if not isinstance(group_by_cols, list):
        raise ToolExecutionError(
            "group_and_aggregate_serializable", 
            "group_by_cols must be a list of column names (can be empty for global aggregation)"
        )
    
    # Convert to DataFrame for processing
    df = pd.DataFrame(data)
    
    # If DataFrame is empty, return early
    if len(df) == 0:
        return {
            'result_df': df,
            'result_data': [],
            'message': "No data to aggregate.",
            'metadata': {
                'original_rows': 0,
                'grouped_rows': 0,
                'group_by_columns': group_by_cols,
                'aggregation_definitions': agg_definitions
            }
        }
    
    # Helper function for case-insensitive column name matching
    def find_actual_column(col_name):
        if col_name in df.columns:
            return col_name
        else:
            # Try case-insensitive matching
            col_lower = col_name.lower()
            log_info(f"Trying case-insensitive match for column '{col_name}'", {
                "available_columns": list(df.columns),
                "lowercase_column": col_lower
            })
            for col in df.columns:
                if col.lower() == col_lower:
                    log_info(f"Found matching column: '{col}' for requested column: '{col_name}'")
                    return col
            log_info(f"No matching column found for '{col_name}'")
            return None
    
    # Process group_by columns with case-insensitive matching
    actual_group_by_cols = []
    for col in group_by_cols:
        actual_col = find_actual_column(col)
        if actual_col is None:
            raise ToolExecutionError(
                "group_and_aggregate_serializable",
                f"Group by column '{col}' not found in data. Available columns: {', '.join(df.columns)}"
            )
        actual_group_by_cols.append(actual_col)
    
    if not isinstance(agg_definitions, list) or len(agg_definitions) == 0:
        raise ToolExecutionError(
            "group_and_aggregate_serializable",
            "agg_definitions must be a non-empty list of aggregation definitions"
        )
    
    # Validate and normalize aggregation definitions
    agg_dict = {}
    agg_columns = []
    renamed_columns = {}
    
    for i, agg_def in enumerate(agg_definitions):
        # Check required keys
        if not isinstance(agg_def, dict):
            raise ToolExecutionError(
                "group_and_aggregate_serializable",
                f"Aggregation definition at index {i} must be a dictionary"
            )
        
        if "column" not in agg_def or "function" not in agg_def:
            raise ToolExecutionError(
                "group_and_aggregate_serializable",
                f"Aggregation definition at index {i} missing required keys 'column' and/or 'function'"
            )
        
        col = agg_def["column"]
        func = agg_def["function"]
        
        # Find the actual column name with case-insensitive matching
        actual_col = find_actual_column(col)
        if actual_col is None:
            raise ToolExecutionError(
                "group_and_aggregate_serializable",
                f"Aggregation column '{col}' not found in data. Available columns: {', '.join(df.columns)}"
            )
        col = actual_col
        
        # Validate aggregation function
        supported_functions = ["sum", "mean", "count", "min", "max", "std", "median", "first", "last"]
        if func not in supported_functions:
            raise ToolExecutionError(
                "group_and_aggregate_serializable",
                f"Unsupported aggregation function: '{func}'. Supported functions: {', '.join(supported_functions)}"
            )
        
        # Track column for later checking and build aggregation dictionary
        agg_columns.append(col)
        
        # If no previous aggregation for this column, initialize with a list
        if col not in agg_dict:
            agg_dict[col] = []
        
        # Add the function to the list for this column
        agg_dict[col].append(func)
        
        # Track column renames if specified
        if "new_column_name" in agg_def and agg_def["new_column_name"]:
            # Format for renamed column in pandas: (col, func)
            old_name = f"{col}_{func}" if len(agg_dict[col]) > 1 else col
            renamed_columns[old_name] = agg_def["new_column_name"]
    
    try:
        # If we have groupby columns, perform groupby aggregation
        if actual_group_by_cols:
            grouped_df = df.groupby(actual_group_by_cols, as_index=False).agg(agg_dict)
            groupby_message = f"Data grouped by {', '.join(actual_group_by_cols)} and aggregated successfully."
        else:
            # Otherwise, perform global aggregation
            # We need to create a result dataframe with just the aggregated values
            global_agg = df.agg(agg_dict)
            
            # Transform the result from Series to DataFrame
            grouped_df = pd.DataFrame()
            
            # Process each column and function
            for col, funcs in agg_dict.items():
                for func in funcs:
                    # Get the column name based on rename rules
                    col_name = f"{col}_{func}" if len(funcs) > 1 else col
                    if col_name in renamed_columns:
                        col_name = renamed_columns[col_name]
                    
                    # Get the value from global_agg
                    if isinstance(global_agg, pd.DataFrame):
                        value = global_agg.loc[func, col]
                    else:  # Series
                        value = global_agg[col] if func == funcs[0] else global_agg[f"{col}_{func}"]
                    
                    # Add to result DataFrame
                    grouped_df[col_name] = [value]
            
            groupby_message = "Global aggregation performed successfully across the entire dataset."
        
        # Flatten the column names if using multi-level columns
        if isinstance(grouped_df.columns, pd.MultiIndex):
            grouped_df.columns = [f"{col}_{func}" if col != "" else func for col, func in grouped_df.columns]
        
        # Rename columns if any custom names were provided
        if renamed_columns:
            grouped_df = grouped_df.rename(columns=renamed_columns)
        
        # Convert the result DataFrame to a list of dictionaries
        result_data = grouped_df.to_dict(orient='records')
        
        # Prepare result with metadata
        result = {
            'result_df': grouped_df,  # Include DataFrame for compatibility
            'result_data': result_data,  # Include serializable list of dicts
            'message': groupby_message,
            'metadata': {
                'original_rows': len(df),
                'grouped_rows': len(grouped_df),
                'group_by_columns': actual_group_by_cols,
                'aggregation_definitions': agg_definitions
            }
        }
        
        # Add unique groups if there are groupby columns and not too many groups
        if actual_group_by_cols and len(grouped_df) <= 10:
            result['metadata']['unique_groups'] = grouped_df[actual_group_by_cols].to_dict(orient='records')
        
        return result
    
    except Exception as e:
        # If it's already a ToolExecutionError, re-raise it
        if isinstance(e, ToolExecutionError):
            raise e
        
        # Otherwise wrap it
        raise ToolExecutionError("group_and_aggregate_serializable", str(e))


def create_pivot_table_serializable(data: List[Dict[str, Any]], index: List[str], values: List[str], 
                                  columns: Optional[List[str]] = None, agg_func: str = "mean") -> Dict[str, Any]:
    """
    Creates a pivot table from data.
    
    Args:
        data: List of dictionaries where each dictionary represents a row
        index: Column names to use as the pivot table index (rows)
        values: Column names to use for the values in the pivot table
        columns: Column names to use for the pivot table columns (optional)
        agg_func: Aggregation function to apply (default: "mean")
        
    Returns:
        Dictionary containing the pivot table data and metadata
    """
    # Input validation
    if not isinstance(data, list):
        raise ToolExecutionError("create_pivot_table_serializable", "Data must be a list of dictionaries")
    
    # Convert to DataFrame for processing
    df = pd.DataFrame(data)
    
    # If DataFrame is empty, return early
    if len(df) == 0:
        return {
            'result_df': pd.DataFrame(),
            'result_data': [],
            'message': "No data to pivot.",
            'metadata': {
                'original_rows': 0,
                'pivot_rows': 0,
                'index_columns': index,
                'value_columns': values,
                'pivot_columns': columns,
                'aggregation_function': agg_func
            }
        }
    
    if not isinstance(index, list) or len(index) == 0:
        raise ToolExecutionError(
            "create_pivot_table_serializable",
            "index must be a non-empty list of column names"
        )
    
    # Validate all index columns exist in the DataFrame
    for col in index:
        if col not in df.columns:
            raise ToolExecutionError(
                "create_pivot_table_serializable",
                f"Index column '{col}' not found in data. Available columns: {', '.join(df.columns)}"
            )
    
    if not isinstance(values, list) or len(values) == 0:
        raise ToolExecutionError(
            "create_pivot_table_serializable",
            "values must be a non-empty list of column names"
        )
    
    # Validate all values columns exist in the DataFrame
    for col in values:
        if col not in df.columns:
            raise ToolExecutionError(
                "create_pivot_table_serializable",
                f"Values column '{col}' not found in data. Available columns: {', '.join(df.columns)}"
            )
    
    # Validate columns if provided
    if columns is not None:
        if not isinstance(columns, list) or len(columns) == 0:
            raise ToolExecutionError(
                "create_pivot_table_serializable",
                "columns must be a non-empty list of column names if provided"
            )
        
        # Validate all columns exist in the DataFrame
        for col in columns:
            if col not in df.columns:
                raise ToolExecutionError(
                    "create_pivot_table_serializable",
                    f"Column '{col}' not found in data. Available columns: {', '.join(df.columns)}"
                )
    
    # Validate aggregation function
    supported_functions = ["sum", "mean", "count", "min", "max", "std", "median", "first", "last"]
    if agg_func not in supported_functions:
        raise ToolExecutionError(
            "create_pivot_table_serializable",
            f"Unsupported aggregation function: '{agg_func}'. Supported functions: {', '.join(supported_functions)}"
        )
    
    try:
        # Create the pivot table
        pivot_df = pd.pivot_table(
            df,
            index=index,
            values=values,
            columns=columns,
            aggfunc=agg_func
        )
        
        # Reset index to make it a regular DataFrame
        pivot_df = pivot_df.reset_index()
        
        # Flatten column names if multi-level
        if isinstance(pivot_df.columns, pd.MultiIndex):
            # Create more readable column names
            if columns:
                # If we have both multiple values and columns, use both in name
                if len(values) > 1:
                    pivot_df.columns = [f"{val}_{col}" if col != "" and val != "" else (col or val) 
                                      for val, col in pivot_df.columns]
                # If we have only one value column but multiple pivot columns
                else:
                    pivot_df.columns = [f"{values[0]}_{col}" if col != "" and col is not None else values[0] 
                                       for col in pivot_df.columns.get_level_values(-1)]
            else:
                # If we only have multiple value columns but no pivot columns
                pivot_df.columns = [col if not isinstance(col, tuple) else col[-1] for col in pivot_df.columns]
        
        # Convert the result DataFrame to a list of dictionaries
        result_data = pivot_df.to_dict(orient='records')
        
        # Prepare result with metadata
        result = {
            'result_df': pivot_df,  # Include DataFrame for compatibility
            'result_data': result_data,  # Include serializable list of dicts
            'message': f"Pivot table created successfully with {index} as index and {values} as values.",
            'metadata': {
                'original_rows': len(df),
                'pivot_rows': len(pivot_df),
                'index_columns': index,
                'value_columns': values,
                'pivot_columns': columns,
                'aggregation_function': agg_func
            }
        }
        
        return result
    
    except Exception as e:
        # If it's already a ToolExecutionError, re-raise it
        if isinstance(e, ToolExecutionError):
            raise e
        
        # Otherwise wrap it
        raise ToolExecutionError("create_pivot_table_serializable", str(e)) 