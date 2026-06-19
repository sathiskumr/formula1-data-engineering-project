"""
Unit tests for ingestion_helpers.py

HOW TO RUN:
    pytest tests/test_ingestion_helpers.py -v

WHAT WE ARE TESTING:
    Our logic only. We never make real HTTP calls.
    requests.get is replaced with a fake (Mock) in every test that needs it.

WHY WE MOCK:
    - Real API calls are slow, flaky, and test Jolpica's code not ours
    - We want tests to pass whether or not there is internet access
    - We control exactly what the fake API returns, so we can test every branch

STRUCTURE:
    One test class per function. Each method inside is one test case.
    Test method names follow: test_<what it does>_<expected outcome>
"""

import pytest
from datetime import date
from unittest.mock import patch, MagicMock

from ingestion_helpers import (
    validate_batch_inputs,
    fetch_paginated,
    parse_results,
    parse_sprints,
    parse_drivers
)


# ---------------------------------------------------------------------------
# validate_batch_inputs
# ---------------------------------------------------------------------------

class TestValidateBatchInputs:
    """
    validate_batch_inputs has three responsibilities:
      1. Raise ValueError if season is empty
      2. Raise ValueError if round_no is empty
      3. Return a correctly zero-padded batch_id when both are valid
    One test per responsibility.
    """

    def test_empty_season_raises(self):
        # Arrange: season is empty, round_no is fine
        # Act + Assert: calling the function should raise ValueError
        # pytest.raises is the pytest way of asserting an exception is thrown
        with pytest.raises(ValueError, match="Both p_season and p_round_no must be provided."):
            validate_batch_inputs("", "2")

    def test_empty_round_raises(self):
        with pytest.raises(ValueError, match="Both p_season and p_round_no must be provided."):
            validate_batch_inputs("2025", "")

    def test_valid_inputs_return_padded_batch_id(self):
        # round_no "2" should become "02" in the batch_id
        result = validate_batch_inputs("2025", "2")
        assert result == "2025-02"

    def test_already_padded_round_unchanged(self):
        # round_no "12" should stay "12", not become "012"
        result = validate_batch_inputs("2025", "12")
        assert result == "2025-12"

    def test_non_numeric_season_raises(self):
        with pytest.raises(ValueError, match="p_season must be numeric"):
            validate_batch_inputs("abc", "2")

    def test_non_numeric_round_raises(self):
        with pytest.raises(ValueError, match="p_round_no must be numeric"):
            validate_batch_inputs("2025", "abc")

    def test_season_before_1950_raises(self):
        with pytest.raises(ValueError, match="p_season=1800 is out of range"):
            validate_batch_inputs("1800", "1")

    def test_season_in_future_raises(self):
        future_year = date.today().year + 1
        with pytest.raises(ValueError, match="is out of range"):
            validate_batch_inputs(str(future_year), "1")

    def test_round_zero_raises(self):
        with pytest.raises(ValueError, match="p_round_no=0 is out of range"):
            validate_batch_inputs("2025", "0")

    def test_round_above_max_raises(self):
        with pytest.raises(ValueError, match="p_round_no=99 is out of range"):
            validate_batch_inputs("2025", "99")


# ---------------------------------------------------------------------------
# fetch_paginated
# ---------------------------------------------------------------------------

class TestFetchPaginated:
    """
    fetch_paginated has two code paths:
      1. Total records fit in one page  → one API call, returns that page's records
      2. Total records span multiple pages → N API calls, returns all records combined

    We also test that an HTTP error from the API bubbles up correctly.

    HOW THE MOCK WORKS HERE:
        @patch("ingestion_helpers.requests.get") intercepts every call to
        requests.get *inside ingestion_helpers.py* and replaces it with a
        MagicMock we control. We then configure what .json() returns on
        each successive call using side_effect (a list of return values).
    """

    @patch("ingestion_helpers.requests.get")
    def test_single_page_returns_all_records(self, mock_get):
        """
        Scenario: API reports total=2, limit=100 → only one page needed.
        Expected: fetch_paginated makes exactly 1 HTTP call and returns both records.
        """
        # Arrange
        # mock_get is the fake that replaced requests.get
        # We configure what its .json() method returns
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "MRData": {
                "total": "2",                        # API always returns total as a string
                "RaceTable": {
                    "Races": [
                        {"round": "1", "season": "2025"},
                        {"round": "2", "season": "2025"},
                    ]
                }
            }
        }
        # raise_for_status should do nothing (no HTTP error)
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Act
        records = fetch_paginated("races/", "RaceTable", "Races", limit=100)

        # Assert
        assert len(records) == 2
        # Confirm we only made 1 HTTP call — no unnecessary pagination
        assert mock_get.call_count == 1

    @patch("ingestion_helpers.requests.get")
    def test_multiple_pages_combines_all_records(self, mock_get):
        """
        Scenario: API reports total=3, limit=2 → 2 pages needed.
        Expected: fetch_paginated makes 2 HTTP calls and returns all 3 records combined.

        side_effect lets us return different values on successive calls.
        First call  → page 1 response (2 records)
        Second call → page 2 response (1 record)
        """
        # Arrange: page 1
        page1 = MagicMock()
        page1.raise_for_status.return_value = None
        page1.json.return_value = {
            "MRData": {
                "total": "3",                        # 3 total records across both pages
                "RaceTable": {
                    "Races": [
                        {"round": "1", "season": "2025"},
                        {"round": "2", "season": "2025"},
                    ]
                }
            }
        }

        # Arrange: page 2
        page2 = MagicMock()
        page2.raise_for_status.return_value = None
        page2.json.return_value = {
            "MRData": {
                "total": "3",
                "RaceTable": {
                    "Races": [
                        {"round": "3", "season": "2025"},
                    ]
                }
            }
        }

        # side_effect: first call returns page1, second call returns page2
        mock_get.side_effect = [page1, page2]

        # Act
        records = fetch_paginated("races/", "RaceTable", "Races", limit=2)

        # Assert
        assert len(records) == 3
        assert mock_get.call_count == 2

        # Also verify the offset in the second call was correct (limit=2, page=1 → offset=2)
        # mock_get.call_args_list holds every call made
        second_call_url = mock_get.call_args_list[1][0][0]   # positional arg of 2nd call
        assert "offset=2" in second_call_url

    @patch("ingestion_helpers.requests.get")
    def test_api_error_raises(self, mock_get):
        """
        Scenario: API returns a 500 status.
        Expected: raise_for_status bubbles the HTTPError up — fetch_paginated does not swallow it.

        We simulate this by making raise_for_status() raise an HTTPError.
        """
        # Arrange
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("500 Server Error")
        mock_get.return_value = mock_response

        # Act + Assert
        with pytest.raises(Exception, match="500 Server Error"):
            fetch_paginated("races/", "RaceTable", "Races")


# ---------------------------------------------------------------------------
# parse_results
# ---------------------------------------------------------------------------

class TestParseResults:
    """
    parse_results has two code paths:
      1. Empty races list  → raise ValueError (round not completed yet)
      2. Non-empty list    → returns correctly shaped records with proper types

    No mocking needed here — parse_results is pure Python logic,
    no HTTP calls. We pass in test data directly.
    """

    def test_empty_races_raises(self):
        with pytest.raises(ValueError, match="No results found"):
            parse_results([])

    def test_returns_correctly_shaped_records(self):
        """
        Pass in a minimal but realistic races payload and verify:
          - Correct number of records returned
          - Types are cast correctly (int, float — not strings)
          - String fields are lowercased where expected
        """
        # Arrange: minimal API-shaped input with one result
        races = [
            {
                "date":     "2025-03-16",
                "raceName": "Australian Grand Prix",   # should be lowercased
                "round":    "3",                        # string from API → should become int
                "season":   "2025",                     # string from API → should become int
                "url":      "https://example.com",
                "Results": [
                    {
                        "Constructor": {"constructorId": "red_bull"},
                        "Driver":      {"driverId": "max_verstappen"},
                        "grid":        "1",
                        "laps":        "57",
                        "number":      "1",
                        "points":      "25",            # string → should become float
                        "position":    "1",
                        "positionText":"1",
                        "status":      "Finished"
                    }
                ]
            }
        ]

        # Act
        records = parse_results(races)

        # Assert: shape
        assert len(records) == 1

        record = records[0]

        # Assert: types — this is the core of the test
        # If someone accidentally removes the int() cast, this will catch it
        assert isinstance(record["round"],    int)
        assert isinstance(record["season"],   int)
        assert isinstance(record["grid"],     int)
        assert isinstance(record["laps"],     int)
        assert isinstance(record["number"],   int)
        assert isinstance(record["points"],   float)
        assert isinstance(record["position"], int)

        # Assert: lowercasing
        assert record["raceName"] == "australian grand prix"

        # Assert: values pass through correctly
        assert record["driverId"] == "max_verstappen"
        assert record["status"]   == "Finished"


# ---------------------------------------------------------------------------
# parse_sprints
# ---------------------------------------------------------------------------

class TestParseSprints:
    """
    parse_sprints has two code paths:
      1. Empty races list  → return [] (non-sprint round, intentional empty file)
      2. Non-empty list    → return correctly shaped sprint records

    This is the most important behavioural difference from parse_results:
    empty input is NOT an error for sprints. It is the expected state
    for ~18 out of 24 race weekends.
    """

    def test_empty_races_returns_empty_list(self):
        """
        Non-sprint round — should return [] silently, not raise.
        The notebook will write this as an empty JSON array to landing.
        """
        result = parse_sprints([])
        assert result == []

    def test_sprint_round_returns_records(self):
        # Arrange
        races = [
            {
                "date":         "2025-05-03",
                "raceName":     "Miami Grand Prix",
                "round":        "6",
                "season":       "2025",
                "url":          "https://example.com",
                "SprintResults": [
                    {
                        "Constructor": {"constructorId": "ferrari"},
                        "Driver":      {"driverId": "leclerc"},
                        "grid":        "2",
                        "laps":        "19",
                        "number":      "16",
                        "points":      "8",
                        "position":    "2",
                        "positionText":"2",
                        "status":      "Finished"
                    }
                ]
            }
        ]

        # Act
        records = parse_sprints(races)

        # Assert
        assert len(records) == 1

        record = records[0]

        # Types
        assert isinstance(record["round"],    int)
        assert isinstance(record["season"],   int)
        assert isinstance(record["points"],   float)
        assert isinstance(record["position"], int)

        # Lowercasing
        assert record["raceName"] == "miami grand prix"

        # Values
        assert record["driverId"] == "leclerc"

# ---------------------------------------------------------------------------
# parse_drivers
# ---------------------------------------------------------------------------

class TestParseDrivers:
    """
    parse_drivers has one edge case worth its own test class: new or
    incomplete driver entries from the API often have empty-string or
    missing biographical fields.

    dateOfBirth is the critical one — it must become None, not "".
    This is a regression test for the paul_aron MALFORMED_RECORD_IN_PARSING
    failure under FAILFAST during bronze ingestion.
    """

    def test_complete_driver_record(self):
        """A driver with full biographical data — the common case."""
        drivers_raw = [{
            "driverId":    "arundell",
            "givenName":   "Peter",
            "familyName":  "Arundell",
            "dateOfBirth": "1933-11-08",
            "nationality": "British",
            "url":         "http://en.wikipedia.org/wiki/Peter_Arundell"
        }]

        records = parse_drivers(drivers_raw)

        assert len(records) == 1
        record = records[0]
        assert record["driverId"]    == "arundell"
        assert record["name"]        == {"givenName": "peter", "familyName": "arundell"}
        assert record["dateOfBirth"] == "1933-11-08"
        assert record["nationality"] == "british"
        assert record["url"]         == "http://en.wikipedia.org/wiki/Peter_Arundell"

    def test_empty_string_date_of_birth_becomes_none(self):
        """
        Regression test for the paul_aron bug: a new driver entry where
        dateOfBirth, nationality, and url are all returned as "".

        dateOfBirth must become None — json.dumps writes this as `null`,
        which casts cleanly to a nullable DateType. "" does not.
        """
        drivers_raw = [{
            "driverId":    "paul_aron",
            "givenName":   "paul",
            "familyName":  "aron",
            "dateOfBirth": "",
            "nationality": "",
            "url":         ""
        }]

        records = parse_drivers(drivers_raw)
        record  = records[0]

        assert record["dateOfBirth"] is None
        # nationality/url stay as "" — StringType handles empty strings fine
        assert record["nationality"] == ""
        assert record["url"]         == ""

    def test_missing_date_of_birth_key_becomes_none(self):
        """
        Some API responses omit the key entirely rather than returning "".
        Same expected outcome: dateOfBirth -> None.
        """
        drivers_raw = [{
            "driverId":   "paul_aron",
            "givenName":  "paul",
            "familyName": "aron",
            # dateOfBirth key absent entirely
            "nationality": "",
            "url":         ""
        }]

        records = parse_drivers(drivers_raw)
        assert records[0]["dateOfBirth"] is None

    def test_name_fields_are_lowercased(self):
        drivers_raw = [{
            "driverId":    "max_verstappen",
            "givenName":   "Max",
            "familyName":  "Verstappen",
            "dateOfBirth": "1997-09-30",
            "nationality": "Dutch",
            "url":         "http://example.com"
        }]

        records = parse_drivers(drivers_raw)
        assert records[0]["name"]["givenName"]  == "max"
        assert records[0]["name"]["familyName"] == "verstappen"
