from . import FRED_API_BASE_URL, FRED_API_KEY
from pydantic import BaseModel, Field
import requests


class Category(BaseModel):
    id: int
    name: str


category_mapping = ((22, "Interest Rates"), (23, "Banking"), (24, "Monetary Data"), (46, "Financial Indicators"))


def _get_categories(id: int = 1) -> list[Category]:
    categories = []
    url = f"{FRED_API_BASE_URL}/category/children?category_id={id}&file_type=json&api_key={FRED_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        for item in data["categories"]:
            category = Category(id=item["id"], name=item["name"])
            categories.append(category)

    return categories


categories = _get_categories()


class FREDData(BaseModel):
    categories: list[Category] = categories
