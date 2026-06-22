import importlib.util
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLEANER_PATH = PROJECT_ROOT / "textcleaner V1.2.py"


def load_cleaner():
    spec = importlib.util.spec_from_file_location("textcleaner_v1_2", CLEANER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def install_fake_frequency(monkeypatch, cleaner):
    scores = {
        "situación": 5.0,
        "situa ción": 1.0,
        "sobretodo": 4.0,
        "sobre todo": 3.0,
        "final": 5.0,
        "fi nal": 1.0,
        "oficiales": 5.0,
        "ofi ciales": 1.0,
        "geográfica": 5.0,
        "geográfi ca": 1.0,
        "magnífica": 5.0,
        "magnífi ca": 1.0,
        "política": 5.5,
        "politica": 3.9,
        "acción": 5.1,
        "accion": 3.9,
        "construcción": 5.0,
        "construccion": 3.4,
        "común": 5.0,
        "comun": 3.6,
        "mónica": 4.6,
        "monica": 2.5,
    }

    def fake_zipf_frequency(text, lang):
        return scores.get(text, 0.0)

    monkeypatch.setattr(cleaner, "WORDFREQ_AVAILABLE", True)
    monkeypatch.setattr(cleaner, "zipf_frequency", fake_zipf_frequency)


def test_merges_hyphenated_line_break(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)

    cleaned, _ = cleaner.clean_markdown_text("La situa-\nción actual")

    assert cleaned == "La situación actual"


def test_merges_unhyphenated_line_break(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)

    cleaned, _ = cleaner.clean_markdown_text("La situa\nción actual")

    assert cleaned == "La situación actual"


def test_merges_inline_hyphenated_word(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)

    cleaned, _ = cleaner.clean_markdown_text("La situa- ción actual")

    assert cleaned == "La situación actual"


def test_merges_inline_split_word_after_previous_nonmerge(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)

    cleaned, _ = cleaner.clean_markdown_text("Al fi nal hay datos ofi ciales.")

    assert cleaned == "Al final hay datos oficiales."


def test_merges_inline_split_word_before_extended_punctuation(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)

    cleaned, _ = cleaner.clean_markdown_text("La zona geográfi ca— y una magnífi ca noticia.")

    assert cleaned == "La zona geográfica— y una magnífica noticia."


def test_merges_inline_split_word_after_opening_spanish_punctuation(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)

    cleaned, _ = cleaner.clean_markdown_text("Es una ¡magnífi ca noticia!")

    assert cleaned == "Es una ¡magnífica noticia!"


def test_stop_phrase_is_not_merged_and_is_written_to_review_log(monkeypatch, tmp_path):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    source = tmp_path / "source.md"
    output = tmp_path / "source.clean.md"
    source.write_text("Lo hizo sobre todo ayer", encoding="utf-8")

    cleaner.clean_markdown_file(source, output, stop_phrases={"sobre todo"})

    assert output.read_text(encoding="utf-8") == "Lo hizo sobre todo ayer"
    assert not output.with_suffix(".review.log").exists()
    review_log = cleaner.review_log_path_for(output)
    assert review_log.exists()
    assert "sobre todo" in review_log.read_text(encoding="utf-8")


def test_deletion_log_records_removed_content(monkeypatch, tmp_path):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    source = tmp_path / "source.md"
    output = tmp_path / "source.clean.md"
    source.write_text(
        "Texto útil.\n1 línea de índice eliminada\nTexto con nota[12].",
        encoding="utf-8",
    )

    cleaner.clean_markdown_file(source, output)

    deletion_log = output.with_suffix(".deletions.log")
    assert deletion_log.exists()
    log_text = deletion_log.read_text(encoding="utf-8")
    assert "1 línea de índice eliminada" in log_text
    assert "Texto con nota[12]." in log_text


def test_markdown_heading_starting_with_number_is_kept(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)

    cleaned, _ = cleaner.clean_markdown_text("# 1 Introducción\nTexto")

    assert "# 1 Introducción" in cleaned
    assert "Texto" in cleaned


def test_footnote_numbers_are_removed(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)

    cleaned, _ = cleaner.clean_markdown_text("Texto con nota[12].")

    assert cleaned == "Texto con nota."


def test_html_table_is_preserved(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    table = "<table>\n<tr><td>situa- ción</td></tr>\n</table>"

    cleaned, _ = cleaner.clean_markdown_text(table)

    assert cleaned == table


def test_multiline_html_table_is_preserved_before_line_merge(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    table = "<table>\n<tr><td>situa-\nción</td></tr>\n</table>"

    cleaned, _ = cleaner.clean_markdown_text(table)

    assert cleaned == table


def test_stop_phrase_matching_is_case_insensitive(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)

    cleaned, review_hits = cleaner.clean_markdown_text(
        "Sobre todo importa",
        stop_phrases={"sobre todo"},
    )

    assert cleaned == "Sobre todo importa"
    assert review_hits


def test_review_log_is_removed_when_no_review_hits(monkeypatch, tmp_path):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    source = tmp_path / "source.md"
    output = tmp_path / "source.clean.md"
    source.write_text("Sobre todo importa", encoding="utf-8")
    cleaner.clean_markdown_file(source, output, stop_phrases={"sobre todo"})
    review_log = cleaner.review_log_path_for(output)
    assert review_log.exists()

    source.write_text("Nada especial", encoding="utf-8")
    cleaner.clean_markdown_file(source, output, stop_phrases={"sobre todo"})

    assert not review_log.exists()
    assert not output.with_suffix(".review.log").exists()


def test_cli_uses_relative_paths_to_avoid_overwriting_same_stem_files(tmp_path):
    mineru_out = tmp_path / "mineru_raw"
    clean_out = tmp_path / "cleaned"
    pdf_root = tmp_path / "pdf_raw"
    first = mineru_out / "book_a" / "main.md"
    second = mineru_out / "book_b" / "main.md"
    first.parent.mkdir(parents=True)
    second.parent.mkdir(parents=True)
    pdf_root.mkdir()
    first.write_text("Uno", encoding="utf-8")
    second.write_text("Dos", encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(CLEANER_PATH),
            "--mineru-out",
            str(mineru_out),
            "--clean-out",
            str(clean_out),
            "--pdf-root",
            str(pdf_root),
        ],
        check=True,
    )

    assert (clean_out / "book_a__main.clean.md").read_text(encoding="utf-8") == "Uno"
    assert (clean_out / "book_b__main.clean.md").read_text(encoding="utf-8") == "Dos"


def test_reference_section_is_removed_until_next_content_heading(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "\n".join(
        [
            "# Conclusiones",
            "Texto final.",
            "# Referencias bibliográficas",
            "Autor, A. (2020). Título. https://doi.org/xxx",
            "# 2. Nuevo capítulo",
            "Texto siguiente.",
        ]
    )

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert "Autor, A." not in cleaned
    assert "# 2. Nuevo capítulo" in cleaned
    assert "Texto siguiente." in cleaned


def test_distribution_table_heading_does_not_delete_body_sections(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "\n".join(
        [
            "## Objetivos",
            "Texto sobre igualdad de oportunidades.",
            "DISTRIBUCIÓN DE LOS MIEMBROS DEL CONSEJO DE ADMINISTRACIÓN POR GÉNERO",
            "<table><tr><td>Consejo de administración</td><td>8</td></tr></table>",
            "## 3.1.5 Derechos laborales52",
            "## Marco regulatorio",
            "Las condiciones laborales se regulan mediante normas y convenios.",
            "## 3.1.6 Seguridad y salud laboral54",
            "BBVA protege la seguridad y salud de sus empleados.",
        ]
    )

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert "DISTRIBUCIÓN DE LOS MIEMBROS" in cleaned
    assert "Consejo de administración</td><td>8" in cleaned
    assert "## 3.1.5 Derechos laborales" in cleaned
    assert "Las condiciones laborales" in cleaned
    assert "## 3.1.6 Seguridad y salud laboral" in cleaned
    assert "BBVA protege la seguridad" in cleaned


def test_plain_body_line_with_backmatter_prefix_does_not_start_section_deletion(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "\n".join(
        [
            "# Gobierno corporativo",
            "Texto introductorio.",
            "Director de riesgos explica el modelo de control interno del Grupo.",
            "Este párrafo forma parte del cuerpo principal y debe conservarse.",
            "## Director de riesgos y control interno",
            "Este apartado describe las responsabilidades del director de riesgos.",
            "## 2.1 Siguiente apartado",
            "Texto siguiente.",
        ]
    )

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert "Director de riesgos" in cleaned
    assert "cuerpo principal" in cleaned
    assert "## Director de riesgos y control interno" in cleaned
    assert "responsabilidades del director" in cleaned
    assert "## 2.1 Siguiente apartado" in cleaned


def test_publication_guidelines_section_is_removed(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "# Texto\nContenido.\n# NORMAS DE PUBLICACIÓN\n1. Solo se aceptan trabajos originales."

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert cleaned == "# Texto\nContenido."


def test_inline_note_numbers_are_removed_without_touching_years(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = (
        "La balanza comercial agroalimentaria se revisó en 2020 y el resultado fue "
        "positivo para el sector1. También se citan servicios sociales 61; y 20,4%."
    )

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert "sector." in cleaned
    assert "servicios sociales;" in cleaned
    assert "2020" in cleaned
    assert "20,4%" in cleaned


def test_inline_note_cleanup_runs_after_full_line_reconstruction(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = (
        "Rousseau sabía perfectamente que la naturaleza humana tiende al conflicto "
        "y que la razón es esclava de las pasiones 18. Entonces los “príncipes” 19 "
        "liderarían el proceso y formaron parte del Eurocuerpo45."
    )

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert "pasiones." in cleaned
    assert "“príncipes” liderarían" in cleaned
    assert "Eurocuerpo." in cleaned
    assert " 18." not in cleaned
    assert " 19 " not in cleaned
    assert "Eurocuerpo45" not in cleaned


def test_attached_note_numbers_before_lowercase_words_are_removed(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = (
        "Puede acogerse a una Comercializadora de Referencia (COR)14. "
        "Los comparadores de precios19 han mostrado cambios, pero G20 y CO2 se conservan."
    )

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert "(COR)." in cleaned
    assert "precios han" in cleaned
    assert "G20" in cleaned
    assert "CO2" in cleaned


def test_financial_codes_keep_their_numbers(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = (
        "El ratio CET1. La norma NIIF9. El capital AT1. "
        "Los indicadores CO2 y G20. El requerimiento P2R. "
        "El tratamiento contable sigue la norma NIIF 9. "
        "El capital CET 1 continúa estable y el Tier 2 también."
    )

    cleaned, _ = cleaner.clean_markdown_text(text)

    for code in ("CET1", "NIIF9", "AT1", "CO2", "G20", "P2R"):
        assert code in cleaned
    for term in ("NIIF 9", "CET 1", "Tier 2"):
        assert term in cleaned


def test_attached_stage_number_is_not_removed(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)

    cleaned, _ = cleaner.clean_markdown_text("La exposición stage3 continúa en seguimiento.")

    assert "stage3 continúa" in cleaned


def test_stage_number_with_attached_footnote_is_repaired(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)

    cleaned, _ = cleaner.clean_markdown_text(
        "El riesgo contingente permanece en stage 39 con las siguientes contrapartidas."
    )

    assert "stage 3 con" in cleaned
    assert "stage 39" not in cleaned


def test_metadata_note_and_toc_reference_lines_are_removed(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "\n".join(
        [
            "Contenido útil.",
            "Referencias bibliográficas 50",
            "BIBLIOGRAFÍA.. 261",
            "BIBLIOGRAFÍA",
            "NOTAS",
            "Bibliografía básica sobre el islam 168",
            "NOTAS: Fuente de una tabla.",
        ]
    )

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert cleaned == "Contenido útil."


def test_comma_note_numbers_are_removed_but_chapter_numbers_remain(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = (
        "Fue el propio de un actor de reparto 50, ni siquiera un secundario. "
        "RCEP: Chapter 12 Electronic Commerce."
    )

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert "reparto, ni siquiera" in cleaned
    assert "Chapter 12 Electronic Commerce" in cleaned


def test_g20_and_historical_numbers_before_commas_are_kept(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "A diferencia de lo ocurrido en la crisis del 29, la coordinación a través del G20, y la OMC se mantiene."

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert "crisis del 29," in cleaned
    assert "G20," in cleaned


def test_lost_spanish_accents_are_restored_when_accented_form_is_more_common(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)

    cleaned, _ = cleaner.clean_markdown_text(
        "Monica estudia la construccion de una politica comun y una accion exterior."
    )

    assert cleaned == "Mónica estudia la construcción de una política común y una acción exterior."


def test_figure_notes_and_sources_are_kept(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "\n".join(
        [
            "Texto principal.",
            "Fuente: elaboración propia con datos oficiales.",
            "NOTA: Solo se muestran diferencias significativas.",
            "Nota. Calculado por ponderación.",
            "Texto siguiente.",
        ]
    )

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert cleaned == text


def test_book_front_matter_copyright_and_toc_are_removed(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "\n".join(
        [
            "# TÍTULO DEL LIBRO",
            "Copyright © 2024 Editorial",
            "ISBN: 978-1-234",
            "# ÍNDICE",
            "CAPÍTULO 1 .... 9",
            "CAPÍTULO 2 .... 30",
            "# Primer capítulo",
            "Este es el cuerpo del libro.",
        ]
    )

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert "Copyright" not in cleaned
    assert "ISBN" not in cleaned
    assert "ÍNDICE" not in cleaned
    assert "CAPÍTULO 1 .... 9" not in cleaned
    assert cleaned == "# Primer capítulo\nEste es el cuerpo del libro."


def test_formula_blocks_are_removed(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "Antes $$\nR o R E = \\frac {B D I I}{(1 - R A) \\cdot V N I}\n$$ después"

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert cleaned == "Antes después"


def test_inline_double_dollar_formula_is_removed(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "Antes $$R o R E = B D I I / V N I$$ después."

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert cleaned == "Antes después."


def test_inline_tex_fragments_are_removed(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "Antes $W A C C _ { A I }$ después."

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert cleaned == "Antes después."


def test_short_inline_formula_fragments_are_removed(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "Donde $j = f,$ y $X E,$ explican el modelo; donde $P '$ generalmente aplica."

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert cleaned == "Donde y explican el modelo; donde generalmente aplica."


def test_parenthesized_tex_formula_is_removed(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "Antes \\( \\mathsf { X } _ { in } / \\sum _ { i = 1 } X \\) después."

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert cleaned == "Antes después."


def test_single_letter_inline_formula_is_removed(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "donde $p$ es la ponderación relativa y $B;$ identifica la renta. El resultado exige $p < 1$."

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert cleaned == "donde es la ponderación relativa y identifica la renta. El resultado exige."


def test_formula_noise_without_delimiters_is_removed(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "Y lo mismo a nivel desagregado, nuevamen-∑ Min99i=1 te para exportaciones."

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert cleaned == "Y lo mismo a nivel desagregado, nuevamente para exportaciones."


def test_slash_separated_body_words_are_preserved(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "Los empleados disponen de licencias/excedencias y opciones de conciliación."

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert "licencias/excedencias" in cleaned


def test_copyright_page_after_toc_is_removed(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "\n".join(
        [
            "# ÍNDICE",
            "PRÓLOGO",
            "CAPÍTULO 1",
            "# AUTOR",
            "Biografía promocional.",
            "ISBN: 978-84-0000",
            "DEPÓSITO LEGAL: M-1",
            "Texto del cuerpo real.",
        ]
    )

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert "ISBN" not in cleaned
    assert "DEPÓSITO" not in cleaned
    assert cleaned == "Texto del cuerpo real."


def test_split_toc_entries_continue_to_be_removed(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "\n".join(
        [
            "ISBN: 978-84-0000",
            "# ÍNDICE",
            "# 5. USO Y ABUSO DE LA TECNOLOGÍA",
            "",
            "FAMILIA-ESCUELA 145",
            "# 6. PROGRAMAS DE INTERVENCIÓN",
            "Y ESCUELA 169",
            "# Capítulo real",
            "Texto del cuerpo.",
        ]
    )

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert "FAMILIA-ESCUELA 145" not in cleaned
    assert "Y ESCUELA 169" not in cleaned
    assert cleaned == "# Capítulo real\nTexto del cuerpo."


def test_compact_chapter_toc_line_is_removed(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "\n".join(
        [
            "# 3. Recursos propios",
            (
                "3.1. Niveles de capital 33 3.2. Recursos propios 38 "
                "3.3. Requerimientos mínimos 45 3.4. Disposiciones transitorias 50"
            ),
            "# 3.1. Niveles de capital",
            "Contenido principal.",
        ]
    )

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert "Recursos propios 38" not in cleaned
    assert cleaned == (
        "# 3. Recursos propios\n"
        "# 3.1. Niveles de capital\n"
        "Contenido principal."
    )


def test_abbreviations_section_after_toc_is_removed(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "\n".join(
        [
            "ISBN: 978-84-0000",
            "# ÍNDICE",
            "CAPÍTULO I .... 25",
            "# ABREVIATURAS",
            "CC Código Civil.",
            "UE Unión Europea.",
            "# PRESENTACIÓN",
            "Texto del cuerpo.",
        ]
    )

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert "ABREVIATURAS" not in cleaned
    assert "CC Código" not in cleaned
    assert cleaned == "# PRESENTACIÓN\nTexto del cuerpo."


def test_spaced_sumario_front_matter_is_removed(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "\n".join(
        [
            "## En preparación",
            "Revista futura",
            "# MINISTERIO DE INDUSTRIA, COMERCIO Y TURISMO NÚMERO 3155",
            "ISSN: 0214-8307",
            "## S U M A R I O",
            "Autor de portada",
            "Artículo de portada",
            "# PRIMER ARTÍCULO REAL",
            "Texto del cuerpo.",
        ]
    )

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert "MINISTERIO" not in cleaned
    assert "S U M A R I O" not in cleaned
    assert cleaned == "# PRIMER ARTÍCULO REAL\nTexto del cuerpo."


def test_presentation_heading_starts_ice_body(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "\n".join(
        [
            "Copyright: Información Comercial Española, 2022",
            "Artículo del sumario 131 Autor",
            "LOS LIBROS Reseña",
            "# PRESENTACIÓN",
            "Texto del cuerpo.",
        ]
    )

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert "Artículo del sumario" not in cleaned
    assert cleaned == "# PRESENTACIÓN\nTexto del cuerpo."


def test_figure_source_copyright_symbol_does_not_restart_front_matter(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "\n".join(
        [
            "Copyright © 2024 Editorial",
            "## SUMARIO",
            "Presentación .... 1",
            "# Presentación Economía política de la desglobalización",
            "Texto de la presentación.",
            "# Primer artículo",
            "## 1. Introduction",
            "Texto inicial del artículo.",
            "SOURCE: World Energy Council data, produced by © Natural Earth.",
            "## 3. Results",
            "Texto posterior.",
        ]
    )

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert cleaned.startswith("# Presentación Economía política")
    assert "Texto de la presentación." in cleaned
    assert "## 1. Introduction" in cleaned
    assert "SOURCE: World Energy Council data, produced by © Natural Earth." in cleaned
    assert "## 3. Results" in cleaned


def test_copyright_symbol_at_line_start_is_front_matter(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "\n".join(
        [
            "# Libro",
            "© 2024 Editorial Ejemplo",
            "ISBN: 978-84-0000",
            "# Capítulo uno",
            "Texto principal.",
        ]
    )

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert cleaned == "# Capítulo uno\nTexto principal."


def test_publication_ads_are_removed_between_articles(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "\n".join(
        [
            "# Artículo uno",
            "Texto.",
            "# TÍTULOS PUBLICADOS EN 2021",
            "![](images/ad.jpg)",
            "Página web: www.revistasice.com",
            "# Artículo dos",
            "Más texto.",
        ]
    )

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert "TÍTULOS PUBLICADOS" not in cleaned
    assert "ad.jpg" not in cleaned
    assert cleaned == "# Artículo uno\nTexto.\n# Artículo dos\nMás texto."


def test_ice_front_matter_and_toc_are_removed(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "\n".join(
        [
            "Ministerio de Economía, Comercio y Empresa",
            "# INFORMACIÓN COMERCIAL ESPAÑOLA Secretaría de Estado de Comercio",
            "## Consejo editorial",
            "Eduardo Aguilar García, Isabel Álvarez González.",
            "ECPMINECO: 1.ª ed./200/0325",
            "ISSN: 0019-977X",
            "Copyright: Información Comercial Española, 2025",
            "FINANCIACIÓN PARA EL DESARROLLO",
            "## Presentación Carlos Cuerpo",
            "Fiscalidad y movilización de recursos domésticos 1 Carlos Garcimartín",
            "## ANÁLISIS",
            "El comercio de bienes con Reino Unido 185 Gonzalo García Andrés",
            "# PRESENTACIÓN",
            "Carlos Cuerpo",
            "Texto real.",
        ]
    )

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert cleaned.startswith("# PRESENTACIÓN")
    assert "Consejo editorial" not in cleaned
    assert "Fiscalidad y movilización" not in cleaned
    assert "ANÁLISIS" not in cleaned
    assert "Carlos Cuerpo" in cleaned
    assert "Texto real." in cleaned


def test_cuadernos_front_matter_and_toc_are_removed(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "\n".join(
        [
            "# CUADERNOS ECONÓMICOS",
            "FECYT-457/2024 Fecha de certificación: 30 de julio de 2021",
            "CONSEJO CIENTÍFICO Michele Boldrin, Washington University.",
            "ISSN: 0210-2633",
            "# CUADERNOS ECONÓMICOS DE ICE",
            "• Presentación.. e Inmaculada Martínez-Zarzoso 1",
            "• Imports Complementarities in European Manufacturing 33",
            "# Presentación Comercio internacional y cadenas de valor en el nuevo contexto global",
            "Carmen Díaz Mora Universidad de Castilla-La Mancha",
            "Texto real.",
        ]
    )

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert cleaned.startswith("# Presentación Comercio internacional")
    assert "FECYT" not in cleaned
    assert "ISSN" not in cleaned
    assert "Imports Complementarities" not in cleaned
    assert "Texto real." in cleaned


def test_ice_promotional_insert_is_removed_but_next_author_is_kept(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "\n".join(
        [
            "# Artículo uno",
            "Texto útil.",
            "# ¡NUEVAS OPCIONES DE LECTURA Y DESCARGA DISPONIBLES!",
            "![](images/ad.jpg)",
            "PDF",
            "HTML",
            "XML (JATS)",
            "La economía no se detiene. Tu información, tampoco",
            "",
            "Gonzalo García Andrés\\* Rafael Ortega Ripoll\\*\\*",
            "# EL COMERCIO DE BIENES CON REINO UNIDO",
            "Texto siguiente.",
        ]
    )

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert "NUEVAS OPCIONES" not in cleaned
    assert "ad.jpg" not in cleaned
    assert "Gonzalo García Andrés Rafael Ortega Ripoll" in cleaned
    assert "# EL COMERCIO DE BIENES CON REINO UNIDO" in cleaned
    assert "Texto siguiente." in cleaned


def test_newsletter_insert_with_nuestra_is_removed_and_author_is_kept(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "\n".join(
        [
            "# Artículo uno",
            "Texto útil.",
            "# Suscríbete a nuestra newsletter y mantente al día",
            "![](images/newsletter.jpg)",
            "Al suscribirte a la newsletter recibirás novedades.",
            "La economía no se detiene. Tu información, tampoco",
            "",
            "Jordi Brandts Isabel Busom Cristina López-Mayan",
            "# TENDIENDO PUENTES ENTRE LAS CIENCIAS SOCIALES Y LA CIUDADANÍA",
            "Texto siguiente.",
        ]
    )

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert "newsletter" not in cleaned.lower()
    assert "Jordi Brandts Isabel Busom Cristina López-Mayan" in cleaned
    assert "# TENDIENDO PUENTES ENTRE LAS CIENCIAS SOCIALES Y LA CIUDADANÍA" in cleaned


def test_ice_next_issue_ad_is_removed_between_articles(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "\n".join(
        [
            "# Artículo uno",
            "Texto útil.",
            "# CONTENIDOS DEL PRÓXIMO NÚMERO",
            "## Economía del comportamiento para mejorar las políticas públicas",
            "● Intervenciones conductuales tipo nudge en educación superior",
            "## NÚMERO EN PREPARACIÓN",
            "● El acceso a la vivienda en España",
            "## Carlos Garcimartín\\*",
            "# FISCALIDAD Y MOVILIZACIÓN DE RECURSOS DOMÉSTICOS",
            "Texto siguiente.",
        ]
    )

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert "CONTENIDOS DEL PRÓXIMO NÚMERO" not in cleaned
    assert "Intervenciones conductuales" not in cleaned
    assert "## Carlos Garcimartín" in cleaned
    assert "# FISCALIDAD Y MOVILIZACIÓN DE RECURSOS DOMÉSTICOS" in cleaned


def test_issn_editorial_tail_is_removed(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "\n".join(
        [
            "# Artículo",
            "Texto útil.",
            "## ISSN 0019-977X",
            "# INFORMACIÓN COMERCIAL ESPAÑOLA Secretaría de Estado de Comercio",
            "## Consejo editorial",
            "Eduardo Aguilar García, Isabel Álvarez González.",
        ]
    )

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert cleaned == "# Artículo\nTexto útil."


def test_known_repeated_anteriores_fragment_is_repaired(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = (
        "Las ediciones anterio- eventos más relevantes de la agenda internacional: "
        "la Cuarta Conferencia Internacional sobre Financiación para el Desarrollo. "
        "Las ediciones anteriores se celebraron en Monterrey."
    )

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert cleaned == "Las ediciones anteriores se celebraron en Monterrey."


def test_subscription_tail_is_removed(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "\n".join(
        [
            "# Artículo",
            "Texto útil.",
            "# BOLETÍN ECONÓMICO DE INFORMACIÓN COMERCIAL ESPAÑOLA (BICE) ISSN 0214-8307",
            "SUSCRIPCIÓN ANUAL",
            "<table><tr><td>Precio</td></tr></table>",
        ]
    )

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert cleaned == "# Artículo\nTexto útil."


def test_financial_report_legal_notice_is_removed(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "\n".join(
        [
            "# Resultados",
            "Contenido financiero.",
            "## Aviso legal",
            "Este documento se proporciona únicamente con fines informativos.",
        ]
    )

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert cleaned == "# Resultados\nContenido financiero."


def test_prudential_report_annexes_and_glossary_are_removed(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "\n".join(
        [
            "# 8. Riesgo ambiental",
            "Contenido principal.",
            "## Anexos",
            "Anexo I: tabla complementaria.",
            "## Glosario de términos",
            "CET1: capital ordinario.",
        ]
    )

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert cleaned == "# 8. Riesgo ambiental\nContenido principal."


def test_numbered_annual_report_annex_is_preserved(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "\n".join(
        [
            "# Cuentas anuales consolidadas",
            "## ANEXO XII. Informe bancario anual",
            "Este anexo forma parte integrante de las cuentas anuales.",
            "## b. Concentración de riesgos",
            "La exposición se desglosa por actividad y geografía.",
        ]
    )

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert "## ANEXO XII. Informe bancario anual" in cleaned
    assert "Este anexo forma parte integrante" in cleaned
    assert "## b. Concentración de riesgos" in cleaned
    assert "La exposición se desglosa" in cleaned


def test_reference_heading_is_kept_for_section_removal(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "\n".join(
        [
            "# Artículo",
            "Texto útil.",
            "## Bibliografía",
            "Golden, S. (2021). China’s role in the world.",
            "## Página web",
            "International Trade Administration. China guide.",
        ]
    )

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert cleaned == "# Artículo\nTexto útil."


def test_publication_guidelines_examples_are_removed_after_subscription(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "\n".join(
        [
            "# Artículo",
            "Texto útil.",
            "## INFORMACIÓN COMERCIAL ESPAÑOLA. REVISTA DE ECONOMÍA (ICE)",
            "## 1. Título del apartado (1.er nivel)",
            "10. Las notas a pie de página irán integradas en el texto.",
            "## Publicaciones periódicas",
            "Apellido, A. A. (Año). Título.",
        ]
    )

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert cleaned == "# Artículo\nTexto útil."


def test_author_annotation_stars_are_removed(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "Francisco de Castro Fernández\\* Carlos Martínez Mongay\\*\\* Javier Yániz Igal\\*"

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert cleaned == "Francisco de Castro Fernández Carlos Martínez Mongay Javier Yániz Igal"


def test_soft_wrapped_sentences_are_reflowed(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "\n".join(
        [
            "Given the uneven and incomplete global recovery, governments need to maintain supportive policies that can be adapted to economic developments and which",
            "improve the prospects for sustainable and inclusive growth.",
            "La COVID-19 representa el shock global más prominente al que se han tenido que enfrentar las Instituciones Financieras Internacionales (IFI) y el Fondo",
            "Monetario Internacional (FMI o Fondo)— desde su creación.",
        ]
    )

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert "which improve the prospects" in cleaned
    assert "Fondo Monetario Internacional" in cleaned


def test_blank_line_prevents_paragraph_reflow(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "\n".join(
        [
            "Juan Luis Manfredi Sánchez Georgetown University",
            "",
            "La preparación de un número monográfico siempre representa un desafío intelectual.",
        ]
    )

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert cleaned == "\n".join(
        [
            "Juan Luis Manfredi Sánchez",
            "Georgetown University",
            "La preparación de un número monográfico siempre representa un desafío intelectual.",
        ]
    )


def test_spanish_author_affiliation_is_split(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "\n".join(
        [
            "# Artículo",
            "Kathia Michalczewsky Universidad Nacional del Sur",
            "",
            "## Resumen",
            "Texto.",
        ]
    )

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert "Kathia Michalczewsky\nUniversidad Nacional del Sur\n## Resumen" in cleaned


def test_short_named_affiliation_is_split(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "\n".join(
        [
            "# Article",
            "Pau Ruiz Guix Hydrogen Europe",
            "",
            "## Abstract",
            "Text.",
        ]
    )

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert "Pau Ruiz Guix\nHydrogen Europe\n## Abstract" in cleaned


def test_incomplete_text_split_by_image_is_reflowed_before_float(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "\n".join(
        [
            "Es el Instrumento de Apoyo",
            "![](images/figure.jpg)",
            "FUENTE: FMI, Fiscal Monitor (octubre 2021).",
            "Temporal para Mitigar los Riesgos de Desempleo en una Emergencia.",
        ]
    )

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert cleaned == "\n".join(
        [
            "Es el Instrumento de Apoyo Temporal para Mitigar los Riesgos de Desempleo en una Emergencia.",
            "![](images/figure.jpg)",
            "FUENTE: FMI, Fiscal Monitor (octubre 2021).",
        ]
    )


def test_english_bibliographic_references_and_ads_are_removed(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "\n".join(
        [
            "# Article",
            "Useful text.",
            "## Bibliographic references",
            "Andrews, D. & Criscuolo, C. (2013). OECD Publishing.",
            "# ECONOMISTAS",
            "La revista Economistas es una publicación especializada.",
            "# SUSCRÍBETE A LA NEWSLETTER DE REVISTAS ICE Y RECIBE TODAS LAS NOVEDADES EN TU CORREO",
            "![](images/newsletter.jpg)",
            "# Next article",
            "More useful text.",
        ]
    )

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert "Andrews" not in cleaned
    assert "ECONOMISTAS" not in cleaned
    assert "SUSCRÍBETE" not in cleaned
    assert cleaned == "# Article\nUseful text.\n# Next article\nMore useful text."


def test_percent_spacing_and_real_numbers_are_preserved(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = (
        "El 23 de abril se aprobó con 70.000 millones, casi 500.000 millones y "
        "28 manifestaciones. El componente fue 80 % y la cifra alcanzó los 348.380 millones."
    )

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert "El 23 de abril" in cleaned
    assert "70.000 millones" in cleaned
    assert "500.000 millones" in cleaned
    assert "28 manifestaciones" in cleaned
    assert "80%" in cleaned
    assert "348.380 millones" in cleaned


def test_percent_spacing_is_normalized_inside_tables(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    text = "<table><tr><td>80 %</td><td>70 %, 60 %</td></tr></table>"

    cleaned, _ = cleaner.clean_markdown_text(text)

    assert cleaned == "<table><tr><td>80%</td><td>70%, 60%</td></tr></table>"


def test_pdf_assisted_repair_can_restore_unique_thousand_number(monkeypatch):
    cleaner = load_cleaner()
    install_fake_frequency(monkeypatch, cleaner)
    cleaned = "La cifra alcanzó los.380 millones."
    source = "La cifra alcanzó los 348.380 millones."

    assert cleaner.repair_lost_thousand_numbers(cleaned, [source]) == "La cifra alcanzó los 348.380 millones."


def test_split_pdf_parts_are_all_matched(tmp_path):
    cleaner = load_cleaner()
    md_path = tmp_path / "informe.md"
    md_path.write_text("Texto.", encoding="utf-8")
    pdf_dir = tmp_path / "informe"
    pdf_dir.mkdir()
    first = pdf_dir / "informe_1.pdf"
    second = pdf_dir / "informe_2.pdf"
    first.write_bytes(b"%PDF")
    second.write_bytes(b"%PDF")

    assert cleaner.find_matching_pdfs(md_path, tmp_path) == [first, second]


def test_cli_deletes_matching_pdf_after_success(tmp_path):
    mineru_out = tmp_path / "mineru_raw"
    clean_out = tmp_path / "cleaned"
    pdf_root = tmp_path / "pdf_raw"
    mineru_out.mkdir()
    pdf_root.mkdir()
    source = mineru_out / "source.md"
    matching_pdf = pdf_root / "source.pdf"
    source.write_text("Texto útil.", encoding="utf-8")
    matching_pdf.write_bytes(b"%PDF")

    subprocess.run(
        [
            sys.executable,
            str(CLEANER_PATH),
            "--mineru-out",
            str(mineru_out),
            "--clean-out",
            str(clean_out),
            "--pdf-root",
            str(pdf_root),
        ],
        check=True,
    )

    assert (clean_out / "source.clean.md").exists()
    assert not matching_pdf.exists()


def test_split_part_delete_prefers_exact_pdf_match(tmp_path):
    cleaner = load_cleaner()
    md_dir = tmp_path / "informe"
    md_dir.mkdir()
    md_path = md_dir / "informe_1.md"
    md_path.write_text("Texto.", encoding="utf-8")
    first = md_dir / "informe_1.pdf"
    second = md_dir / "informe_2.pdf"
    first.write_bytes(b"%PDF")
    second.write_bytes(b"%PDF")

    matches = cleaner.find_matching_pdfs(md_path, tmp_path)

    assert matches == [first, second]
    assert cleaner.pdfs_to_delete_after_clean(md_path, matches) == [first]
