"""
Nivel 2: Integration tests — flujo real con la API de Anthropic.
Corren antes de merge. Requieren ANTHROPIC_API_KEY.
"""

import pytest
import os
from src.team import build_team, DevState

pytestmark = pytest.mark.integration

skipif_no_key = pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="Requiere ANTHROPIC_API_KEY",
)

TAREA_SIMPLE = """
Crear una función Python `celsius_to_fahrenheit(c: float) -> float`
que convierta grados Celsius a Fahrenheit. Incluir validación de tipos.
"""

TAREA_MEDIA = """
Crear un módulo Python con una clase `Stack` genérica con métodos
push, pop, peek, is_empty y size. Usar type hints y lanzar excepciones
descriptivas cuando corresponda.
"""


def make_initial_state(task: str) -> DevState:
    return {
        "task": task, "plan": "", "code": "", "review_feedback": "",
        "review_approved": False, "security_feedback": "", "security_approved": False,
        "tests": "", "test_results": "", "docs": "", "dependencies": "",
        "changelog": "", "iterations": 0,
    }


@skipif_no_key
class TestFlujoCompleto:

    def test_tarea_simple_llena_todos_los_campos(self):
        """El equipo completa el flujo y escribe en todos los campos del estado."""
        team = build_team()
        result = team.invoke(make_initial_state(TAREA_SIMPLE))

        assert result["plan"] != "",         "El arquitecto no generó plan"
        assert result["code"] != "",         "El coder no generó código"
        assert result["tests"] != "",        "El tester no generó tests"
        assert result["docs"] != "",         "El doc writer no generó docs"
        assert result["dependencies"] != "", "El dep checker no respondió"
        assert result["changelog"] != "",    "El release manager no generó changelog"

    def test_iteraciones_dentro_del_limite(self):
        """El equipo nunca supera el máximo de iteraciones definido."""
        team = build_team()
        result = team.invoke(make_initial_state(TAREA_SIMPLE))
        assert result["iterations"] <= 4, (
            f"Demasiadas iteraciones: {result['iterations']}. "
            "Revisar lógica de routing o límites."
        )

    def test_codigo_implementa_funcion_solicitada(self):
        """El código generado contiene la función pedida en la tarea."""
        team = build_team()
        result = team.invoke(make_initial_state(TAREA_SIMPLE))
        assert "celsius_to_fahrenheit" in result["code"], (
            "El coder no implementó la función pedida"
        )

    def test_tests_referencian_funcion_principal(self):
        """Los tests generados cubren la función principal."""
        team = build_team()
        result = team.invoke(make_initial_state(TAREA_SIMPLE))
        assert "celsius_to_fahrenheit" in result["tests"], (
            "Los tests no cubren la función principal"
        )

    def test_docs_incluyen_guia_de_uso(self):
        """La documentación tiene sección de uso o README."""
        team = build_team()
        result = team.invoke(make_initial_state(TAREA_SIMPLE))
        docs_lower = result["docs"].lower()
        assert any(kw in docs_lower for kw in ["readme", "uso", "usage", "example"]), (
            "La documentación no incluye guía de uso"
        )

    def test_changelog_es_sustancial(self):
        """El release manager genera un PR description de longitud razonable."""
        team = build_team()
        result = team.invoke(make_initial_state(TAREA_SIMPLE))
        assert len(result["changelog"]) > 100, "El changelog es demasiado corto"

    def test_tarea_media_con_clase(self):
        """El equipo maneja tareas con clases y métodos múltiples."""
        team = build_team()
        result = team.invoke(make_initial_state(TAREA_MEDIA))
        assert "Stack" in result["code"], "El coder no implementó la clase Stack"
        assert result["tests"] != ""
