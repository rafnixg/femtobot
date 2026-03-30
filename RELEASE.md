# Femtobot — Release v0.1.0

Fecha: 2026-03-29

## Resumen

Lanzamiento inicial de Femtobot: un demo/plantilla de agente asíncrono en Python. Esta versión incorpora mejoras de documentación interna (docstrings), un `README.md` más completo, pruebas básicas, y un flujo de CI para construir y publicar la documentación HTML en GitHub Pages.

## Highlights

- Docstrings: documentación interna ampliada y aclarada en `femtobot.py`.
- README: nuevo `README.md` con arquitectura, uso y ejemplos.
- Tests: `tests/test_femtobot.py` añadido; pruebas locales pasan (4 tests).
- Dependencias: `requirements.txt` con `openai==2.14.0`.
- CI / Docs: `.github/workflows/build-doc.yml` creado/ajustado para construir documentación pdoc y desplegarla en GitHub Pages (patrón build → artifact → deploy).
- Bugfix: corrección en `ContextBuilder.build_system_prompt` para retornar `str` en lugar de tupla; varias limpiezas de indentación y formato.

## Cambios técnicos (resumen por archivo)

- `femtobot.py`: Reescritura y limpieza; docstrings ampliados; corrección de comportamiento en el builder del prompt del sistema; documentación de contratos para `Tool`, `ToolRegistry`, `AgentLoop`, `SessionManager` y adaptador LLM.
- `README.md`: Documentación del proyecto, instrucciones para Windows, ejemplo de sesión CLI y pasos futuros.
- `requirements.txt`: Pin de `openai==2.14.0`.
- `tests/test_femtobot.py`: Tests unitarios para `DateTimeTool`, `MessageBus`, `ToolRegistry` y `SessionManager`.
- `.github/workflows/build-doc.yml`: Workflow actualizado para generar docs HTML, subir artefacto y publicar en `gh-pages`. Se actualizaron versiones de acciones para evitar deprecaciones.

## Estado de calidad

- Tests locales: 4 passed.
- Documentación generada localmente; despliegue a Pages pendiente de ejecución en GitHub Actions (recomendación: habilitar Pages si es necesario y ejecutar la Action).

## Notas de instalación / uso rápido

Crear entorno e instalar dependencias:

```bash
python -m venv .venv
source .venv/bin/activate   # o .venv\Scripts\activate en Windows
pip install -r requirements.txt
pytest -q
```

Revisar `README.md` para ejemplos de uso y opciones de configuración de la integración LLM.

## Pasos recomendados para publicar este release en GitHub

1. Crear tag semántico localmente:

```bash
git tag -a v0.1.0 -m "Femtobot initial release — docstrings, README, tests, CI/docs"
git push origin v0.1.0
```

2. Crear un Release en GitHub (UI) usando el tag `v0.1.0` o automatizar con `gh release create`.

3. Verificar GitHub Actions en la pestaña Actions; confirmar que el job `build` sube el artefacto `github-pages` y que el job `deploy` publica en `gh-pages`. Habilitar GitHub Pages en Settings si es necesario.

## Limitaciones y próximos pasos sugeridos

- Confirmar ejecución de la Action en el repositorio (las Actions ejecutadas desde forks tienen permisos limitados).
- Añadir CI de tests en cada push/PR para evitar regresiones al editar docstrings.
- Completar ejemplos de uso más detallados en `README.md` si se desea publicar como proyecto reutilizable.

## Créditos

Mejoras realizadas en este ciclo: docstrings, tests, README y flujo de publicación de docs.
