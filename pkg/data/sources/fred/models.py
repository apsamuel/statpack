from . import FRED_API_BASE_URL, FRED_API_KEY
from pydantic import BaseModel, Field
import requests


class Category(BaseModel):
    id: int
    name: str


class Series(BaseModel):
    id: str
    title: str
    frequency: str
    units: str
    seasonal_adjustment: str
    last_updated: str
    observation_start: str
    observation_end: str
    popularity: int
    notes: str | None = None
    # category:


def _get_categories(id: int = 0) -> list[Category]:
    categories = []
    url = f"{FRED_API_BASE_URL}/category/children?category_id={id}&file_type=json&api_key={FRED_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        for item in data["categories"]:
            category = Category(id=item["id"], name=item["name"])
            categories.append(category)
            # Recursively fetch subcategories
            subcategories = _get_categories(id=category.id)
            categories.extend(subcategories)

    return categories


def _get_series(categories: list[Category]) -> list[Series]:
    series_list = []
    for category in categories:
        url = f"{FRED_API_BASE_URL}/category/series?category_id={category.id}&file_type=json&api_key={FRED_API_KEY}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            for item in data["seriess"]:
                series = Series(
                    id=item["id"],
                    title=item["title"],
                    frequency=item["frequency"],
                    units=item["units"],
                    seasonal_adjustment=item["seasonal_adjustment"],
                    last_updated=item["last_updated"],
                    observation_start=item["observation_start"],
                    observation_end=item["observation_end"],
                    popularity=item["popularity"],
                    notes=item.get("notes"),
                )
                series_list.append(series)
    return series_list


# categories = _get_categories()
# series = _get_series(categories)


class Data(BaseModel):
    categories: list[Category]
    series: list[Series]


def get_data_model():
    categories = _get_categories()
    series = _get_series(categories)
    return Data(categories=categories, series=series)
