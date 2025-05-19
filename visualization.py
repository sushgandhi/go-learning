import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, Any, List, Optional, Union
from app.utils.exceptions import ToolExecutionError
from app.utils.helpers import save_plot


def visualize_data_serializable(
    data: List[Dict[str, Any]], 
    plot_type: str, 
    x: str, 
    y: Optional[str] = None,
    color: Optional[str] = None,
    title: Optional[str] = None,
    figsize: Optional[List[float]] = None,
    bins: Optional[int] = None,
    orientation: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generates a visualization of the data.
    
    Args:
        data: List of dictionaries where each dictionary represents a row
        plot_type: Type of plot to generate (bar, line, scatter, histogram, boxplot, pie, etc.)
        x: Column to use for the x-axis (or main data for histogram/pie)
        y: Column to use for the y-axis (not required for histogram, pie)
        color: Column to use for color differentiation (optional)
        title: Title for the plot (optional)
        figsize: Figure size as [width, height] in inches (optional)
        bins: Number of bins for histogram (optional)
        orientation: Orientation of the plot (horizontal, vertical) (optional)
        
    Returns:
        Dictionary containing the plot URL and metadata
    """
    # Input validation
    if not isinstance(data, list):
        raise ToolExecutionError("visualize_data_serializable", "Data must be a list of dictionaries")
    
    # Convert to DataFrame for processing
    df = pd.DataFrame(data)
    
    # Return early if DataFrame is empty
    if len(df) == 0:
        return {
            'message': "No data to visualize.",
            'plot_url': None,
            'metadata': {
                'plot_type': plot_type,
                'x_column': x,
                'y_column': y,
                'color_column': color,
                'title': title,
                'rows_used': 0
            }
        }
    
    if not plot_type:
        raise ToolExecutionError("visualize_data_serializable", "plot_type is required")
    
    # Validate plot type
    supported_plot_types = [
        "bar", "line", "scatter", "histogram", "hist", "boxplot", "box", 
        "pie", "heatmap", "area", "violin", "kde", "density"
    ]
    
    if plot_type.lower() not in supported_plot_types:
        raise ToolExecutionError(
            "visualize_data_serializable",
            f"Unsupported plot type: '{plot_type}'. Supported types: {', '.join(supported_plot_types)}"
        )
    
    # Standardize plot type names
    if plot_type.lower() == "hist":
        plot_type = "histogram"
    elif plot_type.lower() == "box":
        plot_type = "boxplot"
    elif plot_type.lower() == "density":
        plot_type = "kde"
    
    # Validate x column
    if not x:
        raise ToolExecutionError("visualize_data_serializable", "x column is required")
    
    if x not in df.columns:
        raise ToolExecutionError(
            "visualize_data_serializable",
            f"Column '{x}' not found in data. Available columns: {', '.join(df.columns)}"
        )
    
    # Validate y column if required for the plot type
    y_required_plots = ["bar", "line", "scatter", "boxplot", "area"]
    if plot_type.lower() in y_required_plots and not y:
        raise ToolExecutionError(
            "visualize_data_serializable",
            f"y column is required for {plot_type} plots"
        )
    
    if y and y not in df.columns:
        raise ToolExecutionError(
            "visualize_data_serializable",
            f"Column '{y}' not found in data. Available columns: {', '.join(df.columns)}"
        )
    
    # Validate color column if provided
    if color and color not in df.columns:
        raise ToolExecutionError(
            "visualize_data_serializable",
            f"Color column '{color}' not found in data. Available columns: {', '.join(df.columns)}"
        )
    
    # Validate numeric columns for certain plot types
    numeric_required_plots = ["scatter", "line", "histogram", "kde", "area"]
    
    if plot_type.lower() in numeric_required_plots:
        # Check if x is numeric
        if not pd.api.types.is_numeric_dtype(df[x]):
            raise ToolExecutionError(
                "visualize_data_serializable",
                f"Column '{x}' must be numeric for {plot_type} plots"
            )
        
        # Check if y is numeric (if provided and required)
        if y and plot_type.lower() != "histogram" and not pd.api.types.is_numeric_dtype(df[y]):
            raise ToolExecutionError(
                "visualize_data_serializable",
                f"Column '{y}' must be numeric for {plot_type} plots"
            )
    
    # Validate orientation if provided
    if orientation and orientation.lower() not in ["horizontal", "vertical", "h", "v"]:
        raise ToolExecutionError(
            "visualize_data_serializable",
            "orientation must be 'horizontal' or 'vertical'"
        )
    
    # Normalize orientation
    if orientation:
        orientation = "h" if orientation.lower() in ["horizontal", "h"] else "v"
    
    try:
        # Set aesthetic style
        sns.set_style("whitegrid")
        
        # Create figure with specified size or default
        if figsize:
            fig, ax = plt.subplots(figsize=figsize)
        else:
            fig, ax = plt.subplots(figsize=(10, 6))
        
        # Generate the appropriate plot based on type
        if plot_type.lower() == "bar":
            if color:
                # Create grouped bar chart
                pivot_df = df.pivot_table(index=x, columns=color, values=y, aggfunc='mean')
                pivot_df.plot(kind='bar', ax=ax)
            else:
                # Create regular bar chart
                if orientation == "h":
                    sns.barplot(x=y, y=x, data=df, ax=ax)
                else:
                    sns.barplot(x=x, y=y, data=df, ax=ax)
        
        elif plot_type.lower() == "line":
            if color:
                # Create multi-line chart
                for val in df[color].unique():
                    subset = df[df[color] == val]
                    ax.plot(subset[x], subset[y], label=val)
                ax.legend()
            else:
                # Create simple line chart
                ax.plot(df[x], df[y])
        
        elif plot_type.lower() == "scatter":
            # Create scatter plot
            sns.scatterplot(x=x, y=y, hue=color, data=df, ax=ax)
        
        elif plot_type.lower() == "histogram":
            # Create histogram
            sns.histplot(data=df, x=x, bins=bins or 10, ax=ax)
        
        elif plot_type.lower() == "boxplot":
            # Create boxplot
            if orientation == "h":
                sns.boxplot(x=y, y=x, hue=color, data=df, ax=ax)
            else:
                sns.boxplot(x=x, y=y, hue=color, data=df, ax=ax)
        
        elif plot_type.lower() == "pie":
            # Create pie chart - need to aggregate data first
            pie_data = df[x].value_counts()
            ax.pie(pie_data, labels=pie_data.index, autopct='%1.1f%%')
            ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
        
        elif plot_type.lower() == "heatmap":
            # For heatmap, we need a pivot table or correlation matrix
            if y and color:
                # Create pivot table heatmap
                pivot_df = df.pivot_table(index=x, columns=y, values=color, aggfunc='mean')
                sns.heatmap(pivot_df, annot=True, cmap="YlGnBu", ax=ax)
            else:
                # Create correlation heatmap of numeric columns
                numeric_df = df.select_dtypes(include=[np.number])
                correlation = numeric_df.corr()
                sns.heatmap(correlation, annot=True, cmap="coolwarm", ax=ax)
        
        elif plot_type.lower() == "area":
            # Create area plot
            df.plot.area(x=x, y=y, ax=ax)
        
        elif plot_type.lower() == "violin":
            # Create violin plot
            if orientation == "h":
                sns.violinplot(x=y, y=x, hue=color, data=df, ax=ax)
            else:
                sns.violinplot(x=x, y=y, hue=color, data=df, ax=ax)
        
        elif plot_type.lower() == "kde":
            # Create KDE plot
            sns.kdeplot(data=df, x=x, y=y, ax=ax)
        
        # Set plot title if provided
        if title:
            ax.set_title(title)
        else:
            # Generate a default title
            if y:
                ax.set_title(f"{plot_type.capitalize()} of {y} by {x}")
            else:
                ax.set_title(f"{plot_type.capitalize()} of {x}")
        
        # Set axis labels
        ax.set_xlabel(x)
        if y:
            ax.set_ylabel(y)
        
        # Adjust layout
        plt.tight_layout()
        
        # Save the plot and get URL
        plot_url = save_plot(fig)
        
        # Prepare result with metadata
        result = {
            'message': f"{plot_type.capitalize()} plot created successfully.",
            'plot_url': plot_url,
            'metadata': {
                'plot_type': plot_type,
                'x_column': x,
                'y_column': y,
                'color_column': color,
                'title': title or f"{plot_type.capitalize()} of {y or x}",
                'rows_used': len(df)
            }
        }
        
        return result
    
    except Exception as e:
        # If it's already a ToolExecutionError, re-raise it
        if isinstance(e, ToolExecutionError):
            raise e
        
        # Otherwise wrap it
        raise ToolExecutionError("visualize_data_serializable", str(e)) 