import pandas as pd


pwd = __file__.rsplit("/", 1)[0]

def load_file(file_path: str, data_type: str = "csv") -> pd.DataFrame:
    """Load a file into a pandas DataFrame."""
    if data_type == "csv":
        return pd.read_csv(file_path)
    elif data_type == "parquet":
        return pd.read_parquet(file_path)
    else:
        raise ValueError(f"Unsupported data type: {data_type}")

def save_file(df: pd.DataFrame, file_path: str, data_type: str = "csv") -> None:
    """Save a pandas DataFrame to a file."""
    if data_type == "csv":
        df.to_csv(file_path, index=False)
    elif data_type == "parquet":
        df.to_parquet(file_path)
    else:
        raise ValueError(f"Unsupported data type: {data_type}")
    df.to_csv(file_path, index=False)

def load_data(dataset: str, datatype: str = "csv") -> pd.DataFrame:
    """Load a file from the data directory into a pandas DataFrame."""
    if datatype == "csv":
        return pd.read_csv(f"{pwd}/__datasets/{dataset}.csv")
    elif datatype == "parquet":
        return pd.read_parquet(f"{pwd}/{dataset}.parquet")
    else:
        raise ValueError(f"Unsupported data type: {datatype}")

def save_data(df: pd.DataFrame, dataset: str, datatype: str = "csv") -> None:
    """Save a pandas DataFrame to a file in the data directory."""
    if datatype == "csv":
        df.to_csv(f"{pwd}/__datasets/{dataset}.csv", index=False)
    elif datatype == "parquet":
        df.to_parquet(f"{pwd}/__datasets/{dataset}.parquet")
    else:
        raise ValueError(f"Unsupported data type: {datatype}")