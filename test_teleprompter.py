import tempfile
import time
from pathlib import Path

import zipfile

from teleprompter import (
    parse_script, compute_step, format_time, load_script_from_path, latest_in_folder,
    build_word_groups, group_interval_ms, docx_to_text,
)


def test_parse_script_extracts_title_and_text():
    assert parse_script('{"title": "Demo", "text": "Hallo Welt"}') == {"title": "Demo", "text": "Hallo Welt"}


def test_parse_script_defaults_missing_title():
    assert parse_script('{"text": "x"}')["title"] == "Untitled"


def test_parse_script_requires_text_field():
    try:
        parse_script('{"title": "x"}')
        assert False, "should have raised ValueError"
    except ValueError:
        pass


def test_compute_step_scales_with_speed_and_interval():
    assert compute_step(speed_lines_per_sec=2, interval_ms=500) == 1.0
    assert compute_step(speed_lines_per_sec=4, interval_ms=250) == 1.0


def test_format_time_pads_minutes_and_seconds():
    assert format_time(5) == "00:05"
    assert format_time(65) == "01:05"
    assert format_time(0) == "00:00"


def test_load_script_from_path_reads_plain_text_with_filename_as_title():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "intro.txt"
        path.write_text("Hallo aus einer Textdatei", encoding="utf-8")
        result = load_script_from_path(str(path))
        assert result == {"title": "intro", "text": "Hallo aus einer Textdatei"}


def test_load_script_from_path_rejects_unsupported_extension():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "script.pdf"
        path.write_text("x", encoding="utf-8")
        try:
            load_script_from_path(str(path))
            assert False, "should have raised ValueError"
        except ValueError:
            pass


DOCX_DOCUMENT_XML = """<?xml version="1.0"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>Hallo</w:t></w:r><w:r><w:t> Welt</w:t></w:r></w:p>
    <w:p><w:r><w:t>Zweiter Absatz</w:t></w:r></w:p>
  </w:body>
</w:document>"""


def make_fake_docx(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("word/document.xml", DOCX_DOCUMENT_XML)


def test_docx_to_text_extracts_paragraphs():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "script.docx"
        make_fake_docx(path)
        assert docx_to_text(str(path)) == "Hallo Welt\n\nZweiter Absatz"


def test_load_script_from_path_reads_docx_with_filename_as_title():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "intro.docx"
        make_fake_docx(path)
        result = load_script_from_path(str(path))
        assert result == {"title": "intro", "text": "Hallo Welt\n\nZweiter Absatz"}


def test_latest_in_folder_picks_most_recently_modified_supported_file():
    with tempfile.TemporaryDirectory() as tmp:
        older = Path(tmp) / "old.txt"
        newer = Path(tmp) / "new.md"
        ignored = Path(tmp) / "ignored.pdf"
        older.write_text("old", encoding="utf-8")
        ignored.write_text("ignored", encoding="utf-8")
        time.sleep(0.01)
        newer.write_text("new", encoding="utf-8")
        assert latest_in_folder(tmp) == str(newer)


def test_build_word_groups_chunks_three_words_with_char_offsets():
    text = "Eins zwei drei vier fünf"
    groups = build_word_groups(text, group_size=3)
    assert groups == [(0, 14), (15, 24)]
    assert text[groups[0][0]:groups[0][1]] == "Eins zwei drei"
    assert text[groups[1][0]:groups[1][1]] == "vier fünf"


def test_build_word_groups_handles_empty_text():
    assert build_word_groups("") == []


def test_group_interval_ms_scales_inversely_with_speed():
    fast = group_interval_ms(speed_lines_per_sec=4)
    slow = group_interval_ms(speed_lines_per_sec=2)
    assert fast < slow


if __name__ == "__main__":
    test_parse_script_extracts_title_and_text()
    test_parse_script_defaults_missing_title()
    test_parse_script_requires_text_field()
    test_compute_step_scales_with_speed_and_interval()
    test_format_time_pads_minutes_and_seconds()
    test_load_script_from_path_reads_plain_text_with_filename_as_title()
    test_load_script_from_path_rejects_unsupported_extension()
    test_docx_to_text_extracts_paragraphs()
    test_load_script_from_path_reads_docx_with_filename_as_title()
    test_latest_in_folder_picks_most_recently_modified_supported_file()
    test_build_word_groups_chunks_three_words_with_char_offsets()
    test_build_word_groups_handles_empty_text()
    test_group_interval_ms_scales_inversely_with_speed()
    print("All tests passed.")
