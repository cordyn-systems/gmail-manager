from dedupe import ProcessedLog


def test_empty_log_loads_safely(tmp_path) -> None:
    log = ProcessedLog(tmp_path / "processed.csv")
    assert log.load_ids() == set()


def test_add_and_detect_processed_id(tmp_path) -> None:
    log = ProcessedLog(tmp_path / "processed.csv")
    log.add_many(["msg-1"])
    assert log.has_seen("msg-1")
    assert not log.has_seen("msg-2")


def test_add_many_prevents_duplicate_ids(tmp_path) -> None:
    log_path = tmp_path / "processed.csv"
    log = ProcessedLog(log_path)
    log.add_many(["msg-1", "msg-1", "msg-2"])

    loaded = ProcessedLog(log_path)
    assert loaded.load_ids() == {"msg-1", "msg-2"}

