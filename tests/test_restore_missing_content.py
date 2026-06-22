from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "restore_missing_content.py"


def load_restore_module():
    spec = spec_from_file_location("restore_missing_content", SCRIPT_PATH)
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FakeCleaner:
    def __init__(self, cleaned_text):
        self.cleaned_text = cleaned_text

    def clean_markdown_text(self, _source_text):
        return self.cleaned_text, []


def test_plan_restoration_inserts_prose_without_table(tmp_path):
    restore = load_restore_module()
    expected = "\n".join(
        [
            "Texto anterior.",
            "DISTRIBUCIÓN DE EMPLEADOS POR GÉNERO",
            "<table><tr><td>Dato</td></tr></table>",
            "(1) Nota de la tabla.",
            "## 2.1 Derechos laborales",
            "Este primer párrafo principal explica con suficiente detalle las condiciones laborales, los derechos colectivos y las obligaciones aplicables a toda la plantilla del Grupo.",
            "Este segundo párrafo describe la negociación colectiva, los mecanismos de consulta y las garantías establecidas para proteger a todas las personas empleadas.",
            "Este tercer párrafo completa el apartado con información sobre seguridad, salud, conciliación y medidas preventivas adoptadas en las distintas áreas geográficas.",
            "## SIGUIENTE SECCIÓN",
            "Texto posterior.",
        ]
    )
    source = tmp_path / "doc.md"
    target = tmp_path / "doc.clean.md"
    source.write_text("origen", encoding="utf-8")
    target.write_text(
        "Texto anterior.\n## SIGUIENTE SECCIÓN\nTexto posterior.\n",
        encoding="utf-8",
    )

    plan = restore.plan_restoration(
        "doc",
        source,
        target,
        FakeCleaner(expected),
        include_tables=False,
    )

    assert not plan.conflicts
    assert len(plan.insertions) == 1
    assert plan.insertions[0].lines == (
        "## 2.1 Derechos laborales",
        "Este primer párrafo principal explica con suficiente detalle las condiciones laborales, los derechos colectivos y las obligaciones aplicables a toda la plantilla del Grupo.",
        "Este segundo párrafo describe la negociación colectiva, los mecanismos de consulta y las garantías establecidas para proteger a todas las personas empleadas.",
        "Este tercer párrafo completa el apartado con información sobre seguridad, salud, conciliación y medidas preventivas adoptadas en las distintas áreas geográficas.",
    )


def test_include_tables_keeps_table_content(tmp_path):
    restore = load_restore_module()
    expected = "\n".join(
        [
            "Texto anterior.",
            "DISTRIBUCIÓN DE RESULTADOS",
            "<table><tr><td>7.157</td></tr></table>",
            "## 5. Beneficio por acción",
            "Texto recuperado.",
            "## SIGUIENTE SECCIÓN",
        ]
    )
    source = tmp_path / "doc.md"
    target = tmp_path / "doc.clean.md"
    source.write_text("origen", encoding="utf-8")
    target.write_text("Texto anterior.\n## SIGUIENTE SECCIÓN\n", encoding="utf-8")

    plan = restore.plan_restoration(
        "doc",
        source,
        target,
        FakeCleaner(expected),
        include_tables=True,
    )

    assert "DISTRIBUCIÓN DE RESULTADOS" in plan.insertions[0].lines
    assert "<table><tr><td>7.157</td></tr></table>" in plan.insertions[0].lines


def test_missing_table_detection_uses_its_position_not_global_duplicate():
    restore = load_restore_module()
    lines = [
        "Texto anterior.",
        "DISTRIBUCIÓN DE RESULTADOS",
        "<table><tr><td>7.157</td></tr></table>",
        "Texto posterior.",
    ]

    ranges = restore.missing_table_ranges(lines, {0: 0, 3: 1})

    assert ranges == [(1, 3)]


def test_apply_insertions_preserves_all_existing_text():
    restore = load_restore_module()
    original = "Primera línea.\n## Sección existente\nÚltima línea.\n"
    insertion = restore.Insertion(
        expected_start=1,
        expected_end=2,
        target_index=1,
        lines=("Párrafo recuperado.",),
    )

    restored = restore.apply_insertions(original, (insertion,))
    restore.assert_original_text_preserved(original, restored)

    assert restored == (
        "Primera línea.\nPárrafo recuperado.\n"
        "## Sección existente\nÚltima línea.\n"
    )
    assert restored.replace("Párrafo recuperado.\n", "", 1) == original


def test_repeated_text_elsewhere_is_still_restored_at_missing_location():
    restore = load_restore_module()
    repeated = "Este párrafo se publica dos veces en capítulos distintos."
    lines = ["Texto anterior.", repeated, "Texto posterior."]
    matcher = restore.TargetMatcher([repeated])

    selected = restore.select_insertion_lines(
        lines,
        0,
        len(lines),
        include_tables=False,
        matcher=matcher,
    )

    assert selected == tuple(lines)


def test_plain_prose_before_omitted_table_is_preserved():
    restore = load_restore_module()
    lines = [
        "A continuación se detalla la información correspondiente al ejercicio.",
        "<table><tr><td>Dato</td></tr></table>",
        "() Nota extraída de la tabla.",
    ]

    selected = restore.select_insertion_lines(
        lines,
        0,
        len(lines),
        include_tables=False,
        matcher=restore.TargetMatcher([]),
    )

    assert selected == (lines[0],)


def test_visual_rating_labels_are_not_restored_after_body_is_present():
    restore = load_restore_module()
    lines = [
        "## Índices y ratings de sostenibilidad",
        "ESG Score 62 / 100",
        "Score B",
    ]

    selected = restore.select_insertion_lines(
        lines,
        0,
        len(lines),
        include_tables=False,
        matcher=restore.TargetMatcher([]),
        stem="Informe-Anual-BBVA-2023_esp_2",
    )

    assert selected == ()
