import requests
import math

BASE_URL = "https://api.jolpi.ca/ergast/f1"


def validate_batch_inputs(season: str, round_no: str) -> str:
    """
    Validates that season and round_no are non-empty and returns the batch_id.
    This is the same guard that lives at the top of the notebook, extracted
    so it can be tested independently.
    """
    if not season or not round_no:
        raise ValueError("Both p_season and p_round_no must be provided.")
    return f"{season}-{round_no.zfill(2)}"


def fetch_paginated(endpoint: str, data_key: str, record_key: str, limit: int = 100) -> list:
    """
    Fetches all pages from a paginated Jolpica endpoint and returns a flat list of records.

    Args:
        endpoint:   API path segment e.g. "races/", "drivers/"
        data_key:   Top-level key inside MRData e.g. "RaceTable", "DriverTable"
        record_key: Key inside data_key that holds the list e.g. "Races", "Drivers"
        limit:      Page size (default 100, matches Jolpica max)

    Returns:
        Flat list of all records across all pages.
    """
    first_response = requests.get(f"{BASE_URL}/{endpoint}?limit={limit}&offset=0")
    first_response.raise_for_status()
    first_data = first_response.json()

    total       = int(first_data["MRData"]["total"])
    total_pages = math.ceil(total / limit)
    records     = list(first_data["MRData"][data_key][record_key])

    for page in range(1, total_pages):
        response = requests.get(f"{BASE_URL}/{endpoint}?limit={limit}&offset={page * limit}")
        response.raise_for_status()
        records.extend(response.json()["MRData"][data_key][record_key])

    return records


def parse_results(races: list) -> list:
    """
    Parses the Races list from the results API response into a flat list of records.
    Raises ValueError if races is empty (round not yet completed).
    """
    if not races:
        raise ValueError(
            "No results found. Verify the round has been completed and the batch_id is correct."
        )

    race = races[0]
    records = []
    for result in race["Results"]:
        records.append({
            "date":          race["date"],
            "raceName":      race["raceName"].lower(),
            "round":         int(race["round"]),
            "season":        int(race["season"]),
            "url":           race["url"],
            "constructorId": result["Constructor"]["constructorId"],
            "driverId":      result["Driver"]["driverId"],
            "grid":          int(result["grid"]),
            "laps":          int(result["laps"]),
            "number":        int(result["number"]),
            "points":        float(result["points"]),
            "position":      int(result["position"]),
            "positionText":  result["positionText"],
            "status":        result["status"]
        })
    return records


def parse_sprints(races: list) -> list:
    """
    Parses the Races list from the sprint API response.
    Returns an empty list for non-sprint rounds — this is intentional,
    and an empty JSON array will be written to landing for those rounds.
    """
    if not races:
        return []

    sprint_race = races[0]
    records = []
    for result in sprint_race["SprintResults"]:
        records.append({
            "date":          sprint_race["date"],
            "raceName":      sprint_race["raceName"].lower(),
            "round":         int(sprint_race["round"]),
            "season":        int(sprint_race["season"]),
            "url":           sprint_race["url"],
            "constructorId": result["Constructor"]["constructorId"],
            "driverId":      result["Driver"]["driverId"],
            "grid":          int(result["grid"]),
            "laps":          int(result["laps"]),
            "number":        int(result["number"]),
            "points":        float(result["points"]),
            "position":      int(result["position"]),
            "positionText":  result["positionText"],
            "status":        result["status"]
        })
    return records

def parse_drivers(drivers_raw: list) -> list:
    """
    Parses the Drivers list from the drivers API response into a flat list of records.

    New or incomplete driver entries (e.g. recent rookies/reserves) often have
    dateOfBirth, nationality, and url returned as empty strings or omitted
    entirely by the API.

    dateOfBirth specifically must become None (not ""), because the bronze
    schema types it as DateType. An empty string fails FAILFAST parsing with
    MALFORMED_RECORD_IN_PARSING, while null casts cleanly to a nullable
    DateType column.

    nationality/url stay as "" when missing — they're StringType, so an
    empty string is valid and doesn't need the same treatment.
    """
    records = []
    for driver in drivers_raw:
        records.append({
            "driverId": driver["driverId"],
            "name": {
                "givenName":  driver["givenName"].lower(),
                "familyName": driver["familyName"].lower()
            },
            "dateOfBirth": driver.get("dateOfBirth") or None,
            "nationality": driver.get("nationality", "").lower(),
            "url":         driver.get("url", "")
        })
    return records