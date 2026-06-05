"""
Nivel 1: Unit tests — sin llamadas reales a la API.
Corren en segundos. Usar en cada commit.
"""

import json
import pytest
from unittest.mock import MagicMock, patch
from tests.conftest import make_mock_response
from src.team import (
    arquitecto, coder, reviewer, security_auditor,
    tester, doc_writer, dependency_checker, release_manager,
    route_after_review, route_after_security, _run_bandit,
)


# ══════════════════════════════════════════════════════
# ARQUITECTO
# ══════════════════════════════════════════════════════
@pytest.mark.unit
class TestArquitecto:

    def test_genera_plan(self, base_state, mock_api):
        mock_api.messages.create.return_value = make_mock_response(
            "1. Función is_prime\n2. Función get_primes"
        )
        result = arquitecto(base_state)
        assert result["plan"] != ""
        assert result["task"] == base_state["task"]

    def test_llama_con_modelo_opus(self, base_state, mock_api):
        mock_api.messages.create.return_value = make_mock_response("plan")
        arquitecto(base_state)
        assert mock_api.messages.create.call_args.kwargs["model"] == "claude-opus-4-8"

    def test_preserva_campos_no_propios(self, base_state, mock_api):
        mock_api.messages.create.return_value = make_mock_response("plan generado")
        result = arquitecto(base_state)
        assert result["code"] == ""
        assert result["iterations"] == 0


# ══════════════════════════════════════════════════════
# CODER
# ══════════════════════════════════════════════════════
@pytest.mark.unit
class TestCoder:

    def test_incrementa_iteraciones(self, base_state, mock_api):
        mock_api.messages.create.return_value = make_mock_response("def foo(): pass")
        result = coder({**base_state, "plan": "algún plan"})
        assert result["iterations"] == 1

    def test_segunda_iteracion_incluye_review_feedback(self, base_state, mock_api):
        mock_api.messages.create.return_value = make_mock_response("def foo(): pass")
        state = {**base_state, "plan": "plan", "review_feedback": "Falta manejo de errores",
                 "iterations": 1}
        coder(state)
        prompt = mock_api.messages.create.call_args.kwargs["messages"][0]["content"]
        assert "Falta manejo de errores" in prompt

    def test_incluye_security_feedback(self, base_state, mock_api):
        mock_api.messages.create.return_value = make_mock_response("def foo(): pass")
        state = {**base_state, "plan": "plan",
                 "security_feedback": "Inyección SQL detectada", "iterations": 1}
        coder(state)
        prompt = mock_api.messages.create.call_args.kwargs["messages"][0]["content"]
        assert "Inyección SQL detectada" in prompt

    def test_usa_modelo_sonnet(self, base_state, mock_api):
        mock_api.messages.create.return_value = make_mock_response("code")
        coder({**base_state, "plan": "plan"})
        assert mock_api.messages.create.call_args.kwargs["model"] == "claude-sonnet-4-6"


# ══════════════════════════════════════════════════════
# REVIEWER
# ══════════════════════════════════════════════════════
@pytest.mark.unit
class TestReviewer:

    def test_aprueba_cuando_responde_aprobado(self, state_with_code, mock_api):
        mock_api.messages.create.return_value = make_mock_response(
            "DECISION: APROBADO\nFEEDBACK: Código limpio y bien estructurado."
        )
        result = reviewer(state_with_code)
        assert result["review_approved"] is True
        assert "limpio" in result["review_feedback"]

    def test_rechaza_cuando_responde_rechazado(self, state_with_code, mock_api):
        mock_api.messages.create.return_value = make_mock_response(
            "DECISION: RECHAZADO\nFEEDBACK: Falta manejo de edge cases."
        )
        result = reviewer(state_with_code)
        assert result["review_approved"] is False
        assert "edge cases" in result["review_feedback"]

    def test_usa_modelo_opus(self, state_with_code, mock_api):
        mock_api.messages.create.return_value = make_mock_response(
            "DECISION: APROBADO\nFEEDBACK: OK"
        )
        reviewer(state_with_code)
        assert mock_api.messages.create.call_args.kwargs["model"] == "claude-opus-4-8"


# ══════════════════════════════════════════════════════
# SECURITY AUDITOR
# ══════════════════════════════════════════════════════
@pytest.mark.unit
class TestSecurityAuditor:

    def test_aprueba_codigo_limpio(self, state_with_code, mock_api):
        mock_api.messages.create.return_value = make_mock_response(
            "DECISION: APROBADO\nFEEDBACK: Sin vulnerabilidades detectadas."
        )
        with patch("src.team._run_bandit", return_value="bandit: sin hallazgos."):
            result = security_auditor(state_with_code)
        assert result["security_approved"] is True

    def test_rechaza_con_vulnerabilidades(self, state_with_code, mock_api):
        mock_api.messages.create.return_value = make_mock_response(
            "DECISION: RECHAZADO\nFEEDBACK: Inyección de comandos en línea 5."
        )
        with patch("src.team._run_bandit", return_value="bandit: sin hallazgos."):
            result = security_auditor(state_with_code)
        assert result["security_approved"] is False
        assert "inyección" in result["security_feedback"].lower()

    def test_usa_modelo_opus(self, state_with_code, mock_api):
        mock_api.messages.create.return_value = make_mock_response(
            "DECISION: APROBADO\nFEEDBACK: OK"
        )
        with patch("src.team._run_bandit", return_value="bandit: sin hallazgos."):
            security_auditor(state_with_code)
        assert mock_api.messages.create.call_args.kwargs["model"] == "claude-opus-4-8"

    def test_inyecta_reporte_bandit_en_el_prompt(self, state_with_code, mock_api):
        mock_api.messages.create.return_value = make_mock_response(
            "DECISION: APROBADO\nFEEDBACK: OK"
        )
        with patch("src.team._run_bandit", return_value="bandit: 1 hallazgo(s).\n- [HIGH/HIGH] B602 línea 5: subprocess con shell=True"):
            security_auditor(state_with_code)
        prompt = mock_api.messages.create.call_args.kwargs["messages"][0]["content"]
        assert "B602" in prompt
        assert "bandit" in prompt.lower()


# ══════════════════════════════════════════════════════
# _run_bandit (SAST real)
# ══════════════════════════════════════════════════════
@pytest.mark.unit
class TestRunBandit:

    def test_sin_hallazgos(self):
        fake = MagicMock(stdout='{"results": []}', stderr="")
        with patch("src.team.subprocess.run", return_value=fake):
            assert _run_bandit("x = 1") == "bandit: sin hallazgos."

    def test_resume_hallazgos(self):
        report = {
            "results": [{
                "issue_severity": "HIGH", "issue_confidence": "HIGH",
                "test_id": "B602", "line_number": 5,
                "issue_text": "subprocess call with shell=True identified.",
            }]
        }
        fake = MagicMock(stdout=json.dumps(report), stderr="")
        with patch("src.team.subprocess.run", return_value=fake):
            out = _run_bandit("import subprocess")
        assert "1 hallazgo(s)" in out
        assert "B602" in out
        assert "HIGH" in out

    def test_bandit_no_instalado(self):
        with patch("src.team.subprocess.run", side_effect=FileNotFoundError):
            out = _run_bandit("x = 1")
        assert "no está instalado" in out

    def test_json_invalido(self):
        fake = MagicMock(stdout="no soy json", stderr="boom")
        with patch("src.team.subprocess.run", return_value=fake):
            out = _run_bandit("x = 1")
        assert "JSON válido" in out


# ══════════════════════════════════════════════════════
# ROUTING — la lógica más crítica
# ══════════════════════════════════════════════════════
@pytest.mark.unit
class TestRouting:

    def test_reviewer_rechaza_va_a_coder(self, base_state):
        state = {**base_state, "review_approved": False, "iterations": 1}
        assert route_after_review(state) == "coder"

    def test_reviewer_aprueba_va_a_security(self, base_state):
        state = {**base_state, "review_approved": True, "iterations": 1}
        assert route_after_review(state) == "security_auditor"

    def test_max_iteraciones_fuerza_avance_en_review(self, base_state):
        """Después de 3 intentos avanza aunque el reviewer rechace."""
        state = {**base_state, "review_approved": False, "iterations": 3}
        assert route_after_review(state) == "security_auditor"

    def test_security_rechaza_va_a_coder(self, base_state):
        state = {**base_state, "security_approved": False, "iterations": 1}
        assert route_after_security(state) == "coder"

    def test_security_aprueba_va_a_paralelo(self, base_state):
        state = {**base_state, "security_approved": True, "iterations": 1}
        assert route_after_security(state) == "parallel_output"

    def test_security_max_iteraciones_fuerza_avance(self, base_state):
        state = {**base_state, "security_approved": False, "iterations": 4}
        assert route_after_security(state) == "parallel_output"


# ══════════════════════════════════════════════════════
# AGENTES FINALES
# ══════════════════════════════════════════════════════
@pytest.mark.unit
class TestAgentesFinales:

    def test_doc_writer_usa_haiku(self, state_with_code, mock_api):
        mock_api.messages.create.return_value = make_mock_response("# Docs generadas")
        doc_writer(state_with_code)
        assert mock_api.messages.create.call_args.kwargs["model"] == "claude-haiku-4-5"

    def test_dependency_checker_escribe_al_estado(self, state_with_code, mock_api):
        mock_api.messages.create.return_value = make_mock_response("requests==2.31.0")
        result = dependency_checker(state_with_code)
        assert result["dependencies"] != ""

    def test_release_manager_usa_haiku(self, state_with_code, mock_api):
        mock_api.messages.create.return_value = make_mock_response("## CHANGELOG")
        release_manager(state_with_code)
        assert mock_api.messages.create.call_args.kwargs["model"] == "claude-haiku-4-5"

    def test_tester_corre_subprocess(self, state_with_code, mock_api):
        mock_api.messages.create.return_value = make_mock_response("def test_foo(): pass")
        with patch("src.team.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="1 passed", stderr="")
            result = tester(state_with_code)
        assert result["tests"] != ""
        assert result["test_results"] != ""
        mock_run.assert_called_once()
