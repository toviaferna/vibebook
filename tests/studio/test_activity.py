import pytest

from audiol.studio.activity import BookActivity, BookBusy


def test_activity_reserves_one_kind_per_book():
    activity = BookActivity()
    lease = activity.reserve("book-1", "convert")

    assert activity.active("book-1") == "convert"
    with pytest.raises(BookBusy):
        activity.reserve("book-1", "resegment")

    activity.release(lease)
    assert activity.active("book-1") is None


def test_stale_lease_cannot_release_new_activity():
    activity = BookActivity()
    first = activity.reserve("book-1", "convert")
    activity.release(first)
    second = activity.reserve("book-1", "resegment")

    activity.release(first)

    assert activity.active("book-1") == "resegment"
    activity.release(second)
    assert activity.active("book-1") is None


def test_activity_allows_different_books():
    activity = BookActivity()
    first = activity.reserve("book-1", "convert")
    second = activity.reserve("book-2", "resegment")

    assert activity.active("book-1") == "convert"
    assert activity.active("book-2") == "resegment"

    activity.release(first)
    activity.release(second)
