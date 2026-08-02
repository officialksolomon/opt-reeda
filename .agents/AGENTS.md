# Project Rules and Guidelines

## Application Documentation Requirement
* **Mandatory App Documentation:** Every Django application (existing or newly created) must always have a corresponding documentation file in the `docs/` folder (e.g., `docs/<app_name>_prd.rst`) for easy understanding.
* **Content:** This documentation must include a high-level overview, a Product Requirements Document (PRD), architectural flowcharts (using Mermaid), model descriptions, and API summaries.
* **Registration:** Always remember to add any new documentation file to the `toctree` in `docs/index.rst`.

## Virtual Environment
* **Always Activate Virtual Environment:** Before running any Python command, installing packages, or running project scripts, always ensure the command runs within the project's virtual environment context. Either activate it first (`.venv\Scripts\Activate.ps1`) or run commands using `uv run` (e.g., `uv run python <command>` or `uv run pip install <package>`).
