"""Output handling functions for DataFrames."""

import pandas as pd


def write_csv(df: pd.DataFrame, filename: str) -> None:
    """Writes a DataFrame to a CSV file.

    Args:
        df (pd.DataFrame): The DataFrame to write.
        filename (str): The name of the file to write to.
    """
    df.to_csv(filename, index=False)


def write_json(df: pd.DataFrame, filename: str) -> None:
    """Writes a DataFrame to a JSON file.

    Args:
        df (pd.DataFrame): The DataFrame to write.
        filename (str): The name of the file to write to.
    """
    df.to_json(filename, orient="records", lines=True)


def describe_frame(df: pd.DataFrame) -> dict:
    """Gathers descriptive statistics about a DataFrame.

    Args:
        df (pd.DataFrame): The DataFrame to describe.

    Returns:
        dict: A dictionary containing descriptive statistics.
    """
    description = {
        "head": df.head().to_dict(),
        "description": df.describe(include="all").to_dict(),
        "columns": df.columns.astype(str).tolist(),
        "shape": df.shape,
        "dtypes": [{k: type(v).__name__} for k, v in df.dtypes.to_dict().items()],
        "missing_values": df.isnull().sum().to_dict(),
        "unique_values": {col: df[col].nunique() for col in df.columns},
        "memory_usage": df.memory_usage(deep=True).to_dict(),
        "sample_data": df.sample(min(5, len(df))).to_dict(orient="records"),  # Up to 5 random samples
    }
    return description


def display_frame(df: pd.DataFrame, max_rows: int = 10) -> None:
    """Displays a DataFrame in a readable format.

    Args:
        df (pd.DataFrame): The DataFrame to display.
        max_rows (int, optional): Maximum number of rows to display. Defaults to 10.
    """
    print(df.head(max_rows).to_string(index=False))
