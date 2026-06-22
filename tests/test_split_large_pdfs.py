from pathlib import Path

from pypdf import PdfReader, PdfWriter

import split_large_pdfs


def create_pdf(path, page_count):
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=100, height=100)
    with path.open("wb") as output:
        writer.write(output)


def test_pdf_over_limit_is_split(tmp_path):
    source = tmp_path / "Example File.pdf"
    output_dir = tmp_path / "split"
    create_pdf(source, 401)

    total_pages, outputs = split_large_pdfs.split_pdf(source, output_dir, 200)

    assert total_pages == 401
    assert [len(PdfReader(str(path)).pages) for path in outputs] == [200, 200, 1]
    assert outputs[0] == output_dir / "Example File" / "Example File_1.pdf"
    assert outputs[2] == output_dir / "Example File" / "Example File_3.pdf"


def test_pdf_at_threshold_is_not_split(tmp_path):
    source = tmp_path / "small.pdf"
    create_pdf(source, 250)

    total_pages, outputs = split_large_pdfs.split_pdf(source, tmp_path / "split", 200)

    assert total_pages == 250
    assert outputs == []


def test_pdf_over_threshold_uses_200_page_parts(tmp_path):
    source = tmp_path / "large.pdf"
    create_pdf(source, 251)

    total_pages, outputs = split_large_pdfs.split_pdf(source, tmp_path / "split", 200)

    assert total_pages == 251
    assert [len(PdfReader(str(path)).pages) for path in outputs] == [200, 51]


def test_existing_complete_part_is_reused(tmp_path):
    source = tmp_path / "large.pdf"
    output_dir = tmp_path / "split"
    create_pdf(source, 251)

    _, first_outputs = split_large_pdfs.split_pdf(source, output_dir, 200)
    first_mtime = first_outputs[0].stat().st_mtime_ns
    _, second_outputs = split_large_pdfs.split_pdf(source, output_dir, 200)

    assert second_outputs == first_outputs
    assert second_outputs[0].stat().st_mtime_ns == first_mtime


def test_old_flat_parts_are_organized(tmp_path):
    output_dir = tmp_path / "split"
    output_dir.mkdir()
    old_first = output_dir / "Book_part001_pages0001-0200.pdf"
    old_second = output_dir / "Book_part002_pages0201-0300.pdf"
    create_pdf(old_first, 200)
    create_pdf(old_second, 100)

    moved = split_large_pdfs.organize_existing_parts(output_dir)

    assert moved == [
        output_dir / "Book" / "Book_1.pdf",
        output_dir / "Book" / "Book_2.pdf",
    ]
    assert not old_first.exists()
    assert not old_second.exists()
    assert len(PdfReader(str(moved[0])).pages) == 200
