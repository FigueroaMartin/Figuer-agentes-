# Contexto del proyecto: Equipo de agentes de desarrollo de software

## Qué es este proyecto

Un **equipo de agentes de IA** construido con LangGraph y la API de Anthropic que automatiza el ciclo completo de desarrollo de software: dado un enunciado de tarea en lenguaje natural, el equipo produce código revisado, testeado, documentado, auditado en seguridad y listo para hacer PR.

---

## Arquitectura del equipo

### Grafo de ejecución (LangGraph)

```
Tarea
  └─→ Arquitecto
        └─→ Coder ◄──────────────────────────────┐
              └─→ Reviewer                        │ rechaza + feedback
                    ├─→ (rechaza) ────────────────┘
                    └─→ (aprueba) → Security Auditor
                                          ├─→ (rechaza) → Coder (loop)
                                          └─→ (aprueba) → [paralelo]
                                                              ├─→ Tester
                                                              ├─→ Doc Writer
                                                              ├─→ Dependency Checker
                                                              └─→ Release Manager
```

El loop entre Reviewer/Security Auditor y Coder es la pieza central: el código mejora iterativamente antes de avanzar. Hay un límite de 3-4 iteraciones como freno de seguridad.

---

## Agentes y modelos

| Agente             | Modelo            | Responsabilidad                                      |
|--------------------|-------------------|------------------------------------------------------|
| Arquitecto         | claude-opus-4-8   | Descompone la tarea, define interfaces y estructura  |
| Coder              | claude-sonnet-4-6 | Escribe el código Python con type hints              |
| Reviewer           | claude-opus-4-8   | Code review: calidad, SOLID, edge cases              |
| Security Auditor   | claude-opus-4-8   | OWASP, CVEs, secrets, inyección                      |
| Tester             | claude-sonnet-4-6 | Genera tests pytest y los ejecuta de verdad          |
| Doc Writer         | claude-haiku-4-5  | Docstrings Google-style + README                     |
| Dependency Checker | claude-haiku-4-5  | Librerías, versiones, licencias, requirements.txt    |
| Release Manager    | claude-haiku-4-5  | PR title, descripción, CHANGELOG, checklist QA       |

**Criterio de asignación de modelos:** Opus 4.8 para roles con decisiones críticas de razonamiento; Sonnet 4.6 para producción en bucle; Haiku 4.5 para tareas bien definidas y de bajo riesgo.

---

## Estado compartido (DevState)

Todos los agentes leen y escriben en un único diccionario TypedDict:

```python
class DevState(TypedDict):
    task: str              # tarea original (inmutable)
    plan: str              # output del Arquitecto
    code: str              # output del Coder (se sobreescribe en cada iteración)
    review_feedback: str   # feedback del Reviewer (se acumula)
    review_approved: bool  # decisión del Reviewer
    security_feedback: str # feedback del Security Auditor
    security_approved: bool
    tests: str             # tests generados por el Tester
    test_results: str      # stdout/stderr de pytest
    docs: str              # documentación generada
    dependencies: str      # análisis de dependencias + requirements.txt
    changelog: str         # PR description + CHANGELOG entry
    iterations: int        # contador de iteraciones (protección anti-loop)
```

---

## Estructura de archivos

```
dev-agent-team/
├── src/
│   ├── __init__.py
│   └── team.py             # agentes, grafo, entry point
├── tests/
│   ├── conftest.py         # fixtures compartidos (base_state, mock_api)
│   ├── unit/
│   │   └── test_agents.py  # tests sin API (mock de Anthropic)
│   ├── integration/
│   │   └── test_team_flow.py  # flujo real con API
│   └── eval/
│       └── test_quality.py    # LLM-as-judge (Claude evalúa los outputs)
├── pytest.ini
├── requirements.txt
└── .env                    # ANTHROPIC_API_KEY=...
```

---

## Convenciones de código

- Todo el código Python es **tipado** (type hints obligatorios)
- Los agentes son **funciones puras**: reciben `DevState`, devuelven `DevState` (patrón `{**state, "campo": valor}`)
- Los prompts de sistema están **hardcodeados** en cada función de agente
- `parse_decision(text)` es el helper estándar para parsear APROBADO/RECHAZADO
- `ask(model, system, user)` es el wrapper sobre `client.messages.create`

---

## Cómo correr el equipo

```bash
# Setup
pip install -r requirements.txt
cp .env.example .env
# Editar .env con tu ANTHROPIC_API_KEY

# Correr el equipo completo
python -m src.team

# Tests por nivel
pytest tests/unit/ -m unit -v                      # sin API, segundos
pytest tests/integration/ -m integration -v -s     # con API real
pytest tests/eval/ -m eval -v -s                   # LLM-as-judge
pytest --cov=src --cov-report=term-missing          # con coverage
```

---

## Problemas conocidos y limitaciones actuales

1. **Paralelismo en LangGraph**: los 4 agentes finales (tester, doc_writer, dependency_checker, release_manager) están conectados desde `parallel_output` pero LangGraph los ejecuta secuencialmente en la versión actual. Para paralelismo real usar `Send` API o asyncio.
2. **Tests del Tester**: el agente genera tests y los corre con `subprocess` en un directorio temporal. Si el código generado tiene dependencias externas no instaladas, los tests fallan. Pendiente: sandbox con dependencias.
3. **Memoria entre sesiones**: el estado no persiste entre ejecuciones. Cada `team.invoke()` empieza desde cero.
4. **Costo**: una ejecución completa con Opus 4.8 en 3 iteraciones puede consumir ~50k tokens. Monitorear con `response.usage`.

---

## Próximos pasos sugeridos

- [ ] Agregar herramientas reales al Coder (linter, formatter)
- [x] Integrar `bandit` en el Security Auditor como herramienta real — `_run_bandit()` corre bandit (SAST) en un temp dir, parsea el JSON y le inyecta los hallazgos al prompt del auditor. Degrada con gracia si bandit no está instalado o el output no es JSON. Cubierto por `TestRunBandit`.
- [ ] Persistencia del estado con `checkpointer` de LangGraph (SQLite o Redis)
- [ ] GitHub Actions: unit tests en cada push, integration antes de merge
- [ ] Endpoint FastAPI para recibir tareas via HTTP
- [ ] Soporte para tareas multi-archivo (el Coder actualmente produce un solo módulo)

---

## Sesión de contexto (resumen de la conversación que generó este proyecto)

Este proyecto surgió en una sesión de onboarding a agentes de IA. El usuario tiene experiencia en programación pero nunca había trabajado con agentes. Se cubrieron en orden:

1. Fundamentos de agentes (ciclo percibir→razonar→actuar→observar, tool use)
2. Tool use básico con la API de Anthropic (cliente Python, bucle while, stop_reason)
3. Arquitectura multi-agente: patrones de coordinación (orquestador, pipeline, grafo)
4. Elección de LangGraph sobre CrewAI para el dominio de desarrollo de software (control fino del flujo, loops condicionales)
5. Diseño del equipo: 8 agentes con roles especializados
6. Asignación de modelos por criticidad del rol (Opus/Sonnet/Haiku)
7. Estrategia de testing: 3 niveles (unit con mocks, integration con API, eval con LLM-as-judge)
8. Implementación completa de los tests

**Para continuar en Claude Code**, el siguiente paso natural es implementar los próximos pasos de la lista de arriba, o agregar herramientas reales a los agentes.
