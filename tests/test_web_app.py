from web_app import extract_sheet_id


def test_extract_sheet_id_from_url() -> None:
    url = "https://docs.google.com/spreadsheets/d/abcDEF_123-xyz/edit#gid=0"
    assert extract_sheet_id(url) == "abcDEF_123-xyz"


def test_extract_sheet_id_accepts_plain_id() -> None:
    assert extract_sheet_id("abcDEF_123-xyz") == "abcDEF_123-xyz"

