from enum import Enum

from pydantic import BaseModel, Field


class WonderDataset(str, Enum):
    """CDC WONDER dataset identifiers for the datarequest controller.

    POST to: https://wonder.cdc.gov/controller/datarequest/{value}

    Note: UCD_1999_2020 ("D76") is confirmed. Other identifiers are
    derived from CDC WONDER HTML page slugs and may require verification
    against the live CDC WONDER web interface.
    """

    # Underlying Cause of Death ICD-10 (1999-2020) — confirmed
    UCD_1999_2020 = "D76"
    # Natality / Births, current (2007-2024)
    NATALITY = "D149"
    # Natality expanded detail (2016-2024)
    NATALITY_EXPANDED = "D66"
    # AIDS Public Use Data, archival (1981-2002)
    AIDS = "AIDS-v2002"
    # United States Cancer Statistics — Incidence (1999-2022)
    CANCER_INCIDENCE = "cancer-v2022"
    # United States Cancer Statistics — Mortality, bridged race (1999-2021)
    CANCER_MORTALITY = "cancermort-v2021"
    # United States Cancer Statistics — Mortality, single race (2018-2023)
    CANCER_MORTALITY_SR = "cancermort-v2022_SR"


class WonderDatasetInfo(BaseModel):
    name: str = Field(..., description="Human-readable dataset name")
    dataset_id: WonderDataset = Field(..., description="CDC WONDER dataset identifier")
    url: str = Field(..., description="CDC WONDER data-request page URL")
    years: str = Field(..., description="Date range covered by the dataset")


class Data(BaseModel):
    datasets: list[WonderDatasetInfo] = Field(
        default_factory=lambda: [
            WonderDatasetInfo(
                name="Underlying Cause of Death (ICD-10)",
                dataset_id=WonderDataset.UCD_1999_2020,
                url="https://wonder.cdc.gov/ucd-icd10.html",
                years="1999-2020",
            ),
            WonderDatasetInfo(
                name="Natality",
                dataset_id=WonderDataset.NATALITY,
                url="https://wonder.cdc.gov/natality-current.html",
                years="2007-2024",
            ),
            WonderDatasetInfo(
                name="Natality Expanded",
                dataset_id=WonderDataset.NATALITY_EXPANDED,
                url="https://wonder.cdc.gov/natality-expanded-current.html",
                years="2016-2024",
            ),
            WonderDatasetInfo(
                name="AIDS Public Use Data",
                dataset_id=WonderDataset.AIDS,
                url="https://wonder.cdc.gov/aids-v2002.html",
                years="1981-2002",
            ),
            WonderDatasetInfo(
                name="United States Cancer Statistics — Incidence",
                dataset_id=WonderDataset.CANCER_INCIDENCE,
                url="https://wonder.cdc.gov/cancer-v2022.html",
                years="1999-2022",
            ),
            WonderDatasetInfo(
                name="United States Cancer Statistics — Mortality (bridged race)",
                dataset_id=WonderDataset.CANCER_MORTALITY,
                url="https://wonder.cdc.gov/cancermort-v2021.html",
                years="1999-2021",
            ),
            WonderDatasetInfo(
                name="United States Cancer Statistics — Mortality (single race)",
                dataset_id=WonderDataset.CANCER_MORTALITY_SR,
                url="https://wonder.cdc.gov/cancermort-v2022_SR.html",
                years="2018-2023",
            ),
        ]
    )

    def get_dataset_by_id(self, dataset_id: str | WonderDataset) -> WonderDatasetInfo | None:
        for ds in self.datasets:
            if ds.dataset_id == dataset_id or ds.dataset_id.value == dataset_id:
                return ds
        return None

    def get_dataset_by_name(self, name: str) -> WonderDatasetInfo | None:
        for ds in self.datasets:
            if ds.name.lower() == name.lower():
                return ds
        return None


def get_data_model() -> Data:
    return Data()
