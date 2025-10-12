#!/usr/bin/env bash

# This script imports a dataset into the data directory.
# Usage: ./scripts/import_dataset.sh <path_to_dataset> <dataset_name> <datatype>

if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <path_to_dataset> <dataset_name> <datatype>"
    exit 1
fi

DATASET_PATH=$1
DATASET_NAME=$2
DATATYPE=$3


DATA_DIR="pkg/data/__datasets"

find "$DATASET_PATH" -type f -name "${DATASET_NAME}*.${DATATYPE}" | while read -r file; do
    filename=$(basename "$file")
    filename_no_ext="${filename%.*}"
    in2csv "$file" > "$DATA_DIR/${filename_no_ext}.csv"
    echo "Imported $file to $DATA_DIR/"
done