"""Input handling functions for DataFrames."""

import pandas as pd


def read_json(filename: str) -> pd.DataFrame:
    """Reads a JSON file into a DataFrame.

    Args:
        filename (str): The name of the file to read from.

    Returns:
        pd.DataFrame: The DataFrame containing the JSON data.
    """
    return pd.read_json(filename, orient="records", lines=True)


def read_csv(filename: str) -> pd.DataFrame:
    """Reads a CSV file into a DataFrame.

    Args:
        filename (str): The name of the file to read from.

    Returns:
        pd.DataFrame: The DataFrame containing the CSV data.
    """
    return pd.read_csv(filename)
