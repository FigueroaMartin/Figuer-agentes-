"""Fixtures compartidos para todos los niveles de tests."""

import pytest
from unittest.mock import MagicMock, patch
from src.team import DevState


# ── Estados reutilizables ──────────────────────────────────────────────────────

@pytest.fixture
def base_state() -> DevState:
    return {
        "task": "Crear función que dado un número N devuelva los primeros N primos.",
        "plan": "", "code": "", "review_feedback": "", "review_approved": False,
        "security_feedback": "", "security_approved": False,
        "tests": "", "test_results": "", "docs": "",
        "dependencies": "", "changelog": "", "iterations": 0,
    }


@pytest.fixture
def state_with_code(base_state) -> DevState:
    """Estado con código ya generado, para testear agentes downstream."""
    return {
        **base_state,
        "plan": "1. Función is_prime(n). 2. Función get_primes(n) que usa is_prime.",
        "code": """
def is_prime(n: int) -> bool:
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True

def get_primes(count: int) -> list[int]:
    if count < 0:
        raise ValueError("count debe ser >= 0")
    primes = []
    candidate = 2
    while len(primes) < count:
        if is_prime(candidate):
            primes.append(candidate)
        candidate += 1
    return primes
""".strip(),
    }


# ── Mock de la API de Anthropic ───────────────────────────────────────────────

@pytest.fixture
def mock_api():
    """Reemplaza client.messages.create con una respuesta configurable."""
    with patch("src.team.client") as mock_client:
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="respuesta mock por defecto")]
        mock_client.messages.create.return_value = mock_response
        yield mock_client


def make_mock_response(text: str) -> MagicMock:
    """Helper para crear respuestas mock con texto específico."""
    resp = MagicMock()
    resp.content = [MagicMock(text=text)]
    return resp
