import requests
import math
from datetime import date
 
BASE_URL = "https://api.jolpi.ca/ergast/f1"
MIN_SEASON = 1950       # First F1 World Championship season
MAX_ROUND  = 30         # Generous upper bound — no F1 season has exceeded 24 races


def validate_batch_inputs(season: str, round_no: str) -> str:
    """
    Validates season and round_no and returns the zero-padded batch_id.

    Performs cheap, static sanity checks on the manual-override path:
      - both values provided and numeric
      - season between MIN_SEASON (1950) and the current year
      - round_no between 1 and MAX_ROUND (30)

    These catch obvious typos (e.g. season=1800, round_no=99) instantly,
    without an API call. They do NOT guarantee the (season, round) pair
    corresponds to a race that has actually happened — a season/round
    that passes these checks but doesn't exist (e.g. round 20 of a
    20-race season that's still ongoing) is caught downstream when
    parse_results raises "No results found" on an empty API response.
    """
    if not season or not round_no:
        raise ValueError("Both p_season and p_round_no must be provided.")

    try:
        season_int = int(season)
    except ValueError:
        raise ValueError(f"p_season must be numeric, got '{season}'.")

    try:
        round_int = int(round_no)
    except ValueError:
        raise ValueError(f"p_round_no must be numeric, got '{round_no}'.")

    current_year = date.today().year
    if not (MIN_SEASON <= season_int <= current_year):
        raise ValueError(
            f"p_season={season_int} is out of range. "
            f"Must be between {MIN_SEASON} (first F1 season) and {current_year} (current year)."
        )

    if not (1 <= round_int <= MAX_ROUND):
        raise ValueError(
            f"p_round_no={round_int} is out of range. Must be between 1 and {MAX_ROUND}."
        )

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