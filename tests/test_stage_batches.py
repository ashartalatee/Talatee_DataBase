from app.services.stage_batches import ACTIVE_WINDOW_MS, gudang_status

OLD = ACTIVE_WINDOW_MS + 1


def test_failed_and_running():
    assert gudang_status("failed", "INGESTED", 0) == "tinjau"
    assert gudang_status("running", "INGESTED", OLD) == "diproses"


def test_trusted_and_needs_review_do_not_depend_on_age():
    assert gudang_status("success", "TRUSTED", 0) == "bersih"
    assert gudang_status("success", "NEEDS_REVIEW", 0) == "tinjau"


def test_recent_work_shows_as_processing_but_stale_does_not_spin_forever():
    assert gudang_status("success", "INGESTED", 1000) == "diproses"
    assert gudang_status("success", "VALIDATING", 1000) == "diproses"
    assert gudang_status("success", "VALIDATING", OLD) == "bersih"  # lolos validasi, menunggu disetujui
    assert gudang_status("success", "INGESTED", OLD) == "masuk"
