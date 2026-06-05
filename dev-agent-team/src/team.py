"""
Equipo de agentes de desarrollo de software.
Arquitectura: LangGraph + Claude API (Anthropic)
Agentes: Arquitecto, Coder, Reviewer, Security Auditor,
         Tester, Doc Writer, Dependency Checker, Release Manager
"""

import anthropic
import subprocess
import tempfile
import json
import os
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END

client = anthropic.Anthropic()

# ── Modelos por rol ────────────────────────────────────────────────────────────
OPUS   = "claude-opus-4-8"    # razonamiento complejo, decisiones críticas
SONNET = "claude-sonnet-4-6"  # producción: velocidad + calidad
HAIKU  = "claude-haiku-4-5"   # tareas simples, alto volumen, bajo costo


# ── Estado compartido ──────────────────────────────────────────────────────────
class DevState(TypedDict):
    task: str
    plan: str
    code: str
    review_feedback: str
    review_approved: bool
    security_feedback: str
    security_approved: bool
    tests: str
    test_results: str
    docs: str
    dependencies: str
    changelog: str
    iterations: int


# ── Helper ─────────────────────────────────────────────────────────────────────
def ask(model: str, system: str, user: str) -> str:
    r = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return r.content[0].text


def parse_decision(text: str) -> tuple[bool, str]:
    """Extrae APROBADO/RECHAZADO y feedback de una respuesta estructurada."""
    approved = "APROBADO" in text.upper().split("\n")[0]
    feedback = text.split("FEEDBACK:")[-1].strip() if "FEEDBACK:" in text else text
    return approved, feedback


# ── Agentes ───────────────────────────────────────────────────────────────────

def arquitecto(state: DevState) -> DevState:
    print("🏗️  Arquitecto planificando... [Opus 4.8]")
    plan = ask(
        OPUS,
        "Eres un arquitecto de software senior. Descompone la tarea en subtareas "
        "claras con interfaces definidas. Especifica: estructura de archivos, "
        "funciones públicas con sus firmas de tipos, y criterios de aceptación.",
        f"Tarea: {state['task']}",
    )
    return {**state, "plan": plan}


def coder(state: DevState) -> DevState:
    it = state["iterations"] + 1
    print(f"💻  Coder escribiendo... iteración {it} [Sonnet 4.6]")
    ctx = f"Plan:\n{state['plan']}\n\nTarea: {state['task']}"
    if state["review_feedback"]:
        ctx += f"\n\n🔍 Feedback del Reviewer:\n{state['review_feedback']}"
    if state["security_feedback"]:
        ctx += f"\n\n🔒 Feedback del Security Auditor:\n{state['security_feedback']}"
    code = ask(
        SONNET,
        "Eres un desarrollador Python senior. Escribe código limpio, con type hints "
        "completos, manejo de excepciones específicas, y sin hardcodear secrets. "
        "Devuelve SOLO el bloque de código Python, sin markdown.",
        ctx,
    )
    return {**state, "code": code, "iterations": it}


def reviewer(state: DevState) -> DevState:
    print("🔍  Reviewer evaluando calidad... [Opus 4.8]")
    result = ask(
        OPUS,
        "Eres un senior engineer haciendo code review exhaustivo. Evalúa: "
        "correctitud lógica, manejo de errores y edge cases, type hints, "
        "principios SOLID, complejidad ciclomática, y deuda técnica. "
        "Formato OBLIGATORIO:\nDECISION: APROBADO o RECHAZADO\nFEEDBACK: (detallado)",
        f"Código:\n{state['code']}",
    )
    approved, feedback = parse_decision(result)
    print(f"   → {'✅ Aprobado' if approved else '❌ Rechazado'}")
    return {**state, "review_approved": approved, "review_feedback": feedback}


def security_auditor(state: DevState) -> DevState:
    print("🔒  Security Auditor auditando... [Opus 4.8 + bandit]")
    bandit_report = _run_bandit(state["code"])
    result = ask(
        OPUS,
        "Eres un experto en seguridad de aplicaciones. Analiza el código buscando: "
        "inyección SQL/comando, exposición de secrets o credenciales, "
        "vulnerabilidades OWASP Top 10, uso inseguro de librerías, "
        "falta de validación de inputs, y problemas de manejo de errores que "
        "filtren información sensible. Se te provee además el reporte de bandit "
        "(análisis estático SAST): considéralo, pero usa tu criterio (puede tener "
        "falsos positivos/negativos). "
        "Formato OBLIGATORIO:\nDECISION: APROBADO o RECHAZADO\nFEEDBACK: (hallazgos detallados)",
        f"Código a auditar:\n{state['code']}\n\nReporte de bandit (SAST):\n{bandit_report}",
    )
    approved, feedback = parse_decision(result)
    print(f"   → {'🔐 Seguro' if approved else '⚠️  Vulnerabilidades encontradas'}")
    return {**state, "security_approved": approved, "security_feedback": feedback}


def _run_bandit(code: str) -> str:
    """Corre bandit (SAST) sobre el código y devuelve un resumen legible de hallazgos."""
    with tempfile.TemporaryDirectory() as tmp:
        target = os.path.join(tmp, "main.py")
        with open(target, "w", encoding="utf-8") as f:
            f.write(code)
        try:
            result = subprocess.run(
                ["bandit", "-f", "json", "-q", target],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except FileNotFoundError:
            return "bandit no está instalado; análisis estático omitido."
        except subprocess.TimeoutExpired:
            return "bandit excedió el tiempo límite; análisis estático omitido."

    try:
        report = json.loads(result.stdout)
    except (json.JSONDecodeError, ValueError):
        return f"bandit no devolvió JSON válido.\n{result.stdout}{result.stderr}".strip()

    issues = report.get("results", [])
    if not issues:
        return "bandit: sin hallazgos."

    lines = [f"bandit: {len(issues)} hallazgo(s)."]
    for issue in issues:
        lines.append(
            f"- [{issue.get('issue_severity', '?')}/{issue.get('issue_confidence', '?')}] "
            f"{issue.get('test_id', '?')} línea {issue.get('line_number', '?')}: "
            f"{issue.get('issue_text', '').strip()}"
        )
    return "\n".join(lines)


def tester(state: DevState) -> DevState:
    print("🧪  Tester generando y corriendo tests... [Sonnet 4.6]")
    tests = ask(
        SONNET,
        "Eres un QA engineer. Escribe tests con pytest que cubran: happy path, "
        "edge cases, inputs inválidos, y errores esperados. Usa fixtures y mocks "
        "donde corresponda. Solo el código Python de tests.",
        f"Código a testear:\n{state['code']}\n\nTarea original: {state['task']}",
    )
    test_results = _run_tests(state["code"], tests)
    return {**state, "tests": tests, "test_results": test_results}


def _run_tests(code: str, tests: str) -> str:
    """Corre pytest en un directorio temporal y devuelve el resultado."""
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "main.py"), "w") as f:
            f.write(code)
        with open(os.path.join(tmp, "test_main.py"), "w") as f:
            f.write(tests)
        result = subprocess.run(
            ["python", "-m", "pytest", "test_main.py", "-v", "--tb=short"],
            cwd=tmp,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout + result.stderr


def doc_writer(state: DevState) -> DevState:
    print("📝  Doc Writer documentando... [Haiku 4.5]")
    docs = ask(
        HAIKU,
        "Eres un technical writer. Genera: (1) docstrings Google-style para cada "
        "función pública, (2) README.md con descripción, instalación y ejemplos "
        "de uso reales, (3) descripción de tipos y excepciones. Formato markdown.",
        f"Código:\n{state['code']}\n\nTarea: {state['task']}",
    )
    return {**state, "docs": docs}


def dependency_checker(state: DevState) -> DevState:
    print("📦  Dependency Checker verificando... [Haiku 4.5]")
    deps = ask(
        HAIKU,
        "Eres un experto en gestión de dependencias Python. Analiza el código y: "
        "(1) lista todas las librerías externas usadas, (2) sugiere versiones "
        "pinneadas seguras, (3) detecta librerías con CVEs conocidos o "
        "licencias incompatibles con uso comercial, (4) genera el requirements.txt.",
        f"Código:\n{state['code']}",
    )
    return {**state, "dependencies": deps}


def release_manager(state: DevState) -> DevState:
    print("🚀  Release Manager preparando PR... [Haiku 4.5]")
    changelog = ask(
        HAIKU,
        "Eres un release manager. Basándote en la tarea y el código generado, "
        "redacta: (1) título del PR en formato conventional commits, "
        "(2) descripción del PR con contexto y decisiones tomadas, "
        "(3) CHANGELOG entry en formato Keep a Changelog, "
        "(4) checklist de QA para el revisor humano.",
        f"Tarea: {state['task']}\n\nResumen del código:\n{state['code'][:800]}...",
    )
    return {**state, "changelog": changelog}


# ── Routing ────────────────────────────────────────────────────────────────────

def route_after_review(state: DevState) -> Literal["coder", "security_auditor"]:
    if not state["review_approved"] and state["iterations"] < 3:
        return "coder"
    return "security_auditor"


def route_after_security(state: DevState) -> Literal["coder", "parallel_output"]:
    if not state["security_approved"] and state["iterations"] < 4:
        return "coder"
    return "parallel_output"


def parallel_output(state: DevState) -> DevState:
    """Nodo sincronizador antes de los agentes finales en paralelo."""
    return state


# ── Construcción del grafo ─────────────────────────────────────────────────────

def build_team():
    g = StateGraph(DevState)

    g.add_node("arquitecto",         arquitecto)
    g.add_node("coder",              coder)
    g.add_node("reviewer",           reviewer)
    g.add_node("security_auditor",   security_auditor)
    g.add_node("tester",             tester)
    g.add_node("doc_writer",         doc_writer)
    g.add_node("dependency_checker", dependency_checker)
    g.add_node("release_manager",    release_manager)
    g.add_node("parallel_output",    parallel_output)

    g.set_entry_point("arquitecto")
    g.add_edge("arquitecto", "coder")
    g.add_edge("coder", "reviewer")

    g.add_conditional_edges("reviewer", route_after_review, {
        "coder":            "coder",
        "security_auditor": "security_auditor",
    })
    g.add_conditional_edges("security_auditor", route_after_security, {
        "coder":           "coder",
        "parallel_output": "parallel_output",
    })

    g.add_edge("parallel_output", "tester")
    g.add_edge("parallel_output", "doc_writer")
    g.add_edge("parallel_output", "dependency_checker")
    g.add_edge("parallel_output", "release_manager")

    g.add_edge("tester",             END)
    g.add_edge("doc_writer",         END)
    g.add_edge("dependency_checker", END)
    g.add_edge("release_manager",    END)

    return g.compile()


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    team = build_team()

    tarea = """
    Crear un módulo Python que dado un repositorio de GitHub (usuario/repo),
    devuelva las últimas 10 issues abiertas con título, autor y fecha.
    Usar la API pública de GitHub sin autenticación.
    Incluir manejo de rate limiting y errores de red.
    """

    estado_inicial: DevState = {
        "task": tarea, "plan": "", "code": "",
        "review_feedback": "", "review_approved": False,
        "security_feedback": "", "security_approved": False,
        "tests": "", "test_results": "", "docs": "",
        "dependencies": "", "changelog": "", "iterations": 0,
    }

    print("🚀 Iniciando equipo de desarrollo completo...\n")
    r = team.invoke(estado_inicial)

    secciones = [
        ("📦 CÓDIGO FINAL",         "code"),
        ("🧪 TESTS GENERADOS",      "tests"),
        ("📊 RESULTADOS DE TESTS",   "test_results"),
        ("📝 DOCUMENTACIÓN",         "docs"),
        ("📦 DEPENDENCIAS",          "dependencies"),
        ("🚀 PR / CHANGELOG",        "changelog"),
    ]
    for label, key in secciones:
        print(f"\n{'='*60}\n{label}\n{'='*60}\n{r[key]}")
