from audiol.models import make_segment_id


def test_segment_id_includes_chapter_paragraph_and_chunk():
    assert make_segment_id(1, 2, 1) == "c001p0002s01"
    assert make_segment_id(12, 345, 0) == "c012p0345s00"
