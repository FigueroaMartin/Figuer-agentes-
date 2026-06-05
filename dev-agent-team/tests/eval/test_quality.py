"""
Nivel 3: LLM-as-judge — Claude evalúa la calidad de los outputs.
Usar en releases. Requiere ANTHROPIC_API_KEY.
"""

import pytest
import os
import json
import anthropic
from src.team import build_team, DevState

pytestmark = pytest.mark.eval
client = anthropic.Anthropic()

TAREA_EVAL = """
Crear una función Python `paginate(items: list, page: int, page_size: int) -> dict`
que devuelva un diccionario con: items (lista paginada), total, page, pages.
Validar inputs y manejar edge cases (página fuera de rango, page_size <= 0, etc).
"""

UMBRAL_MINIMO = 6  # Score mínimo aceptable sobre 10


def llm_judge(criterio: str, output: str, contexto: str = "") -> dict:
    """Pide a Claude Haiku que evalúe un output con score del 1 al 10."""
    prompt = f"""Evalúa el siguiente output de un agente de IA.

Criterio: {criterio}
{'Contexto: ' + contexto if contexto else ''}

Output a evaluar:
{output[:2000]}

Responde SOLO con JSON válido, sin markdown ni backticks:
{{"score": <número del 1 al 10>, "razon": "<explicación en una oración>"}}"""

    r = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = r.content[0].text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


@pytest.fixture(scope="module")
def team_output():
    """Corre el equipo una sola vez y comparte el resultado entre todos los tests del módulo."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("Requiere ANTHROPIC_API_KEY")

    team = build_team()
    state: DevState = {
        "task": TAREA_EVAL, "plan": "", "code": "", "review_feedback": "",
        "review_approved": False, "security_feedback": "", "security_approved": False,
        "tests": "", "test_results": "", "docs": "", "dependencies": "",
        "changelog": "", "iterations": 0,
    }
    return team.invoke(state)


@pytest.mark.eval
class TestCalidadOutputs:

    def test_calidad_codigo(self, team_output):
        result = llm_judge(
            criterio="¿El código es correcto, tiene type hints, maneja edge cases y es legible?",
            output=team_output["code"],
            contexto=f"Tarea: {TAREA_EVAL}",
        )
        print(f"\n📊 Código — {result['score']}/10 | {result['razon']}")
        assert result["score"] >= UMBRAL_MINIMO, (
            f"Calidad del código insuficiente: {result['score']}/10. {result['razon']}"
        )

    def test_calidad_tests(self, team_output):
        result = llm_judge(
            criterio="¿Los tests cubren happy path, edge cases e inputs inválidos con pytest?",
            output=team_output["tests"],
        )
        print(f"\n📊 Tests — {result['score']}/10 | {result['razon']}")
        assert result["score"] >= UMBRAL_MINIMO, (
            f"Calidad de tests insuficiente: {result['score']}/10. {result['razon']}"
        )

    def test_calidad_docs(self, team_output):
        result = llm_judge(
            criterio="¿La documentación tiene docstrings completos y README con ejemplos de uso?",
            output=team_output["docs"],
        )
        print(f"\n📊 Docs — {result['score']}/10 | {result['razon']}")
        assert result["score"] >= UMBRAL_MINIMO, (
            f"Calidad de documentación insuficiente: {result['score']}/10. {result['razon']}"
        )

    def test_calidad_seguridad(self, team_output):
        result = llm_judge(
            criterio="¿El análisis de seguridad identifica posibles riesgos o confirma código seguro con justificación?",
            output=team_output["security_feedback"],
        )
        print(f"\n📊 Seguridad — {result['score']}/10 | {result['razon']}")
        assert result["score"] >= UMBRAL_MINIMO, (
            f"Análisis de seguridad insuficiente: {result['score']}/10. {result['razon']}"
        )

    def test_calidad_changelog(self, team_output):
        result = llm_judge(
            criterio="¿El changelog y descripción del PR son claros, siguen convenciones estándar e incluyen checklist?",
            output=team_output["changelog"],
        )
        print(f"\n📊 Changelog — {result['score']}/10 | {result['razon']}")
        assert result["score"] >= UMBRAL_MINIMO, (
            f"Changelog insuficiente: {result['score']}/10. {result['razon']}"
        )

    def test_calidad_dependencias(self, team_output):
        result = llm_judge(
            criterio="¿El análisis de dependencias lista librerías con versiones pinneadas y genera requirements.txt?",
            output=team_output["dependencies"],
        )
        print(f"\n📊 Dependencias — {result['score']}/10 | {result['razon']}")
        assert result["score"] >= UMBRAL_MINIMO, (
            f"Análisis de dependencias insuficiente: {result['score']}/10. {result['razon']}"
        )
