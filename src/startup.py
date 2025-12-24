from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StartupContext:
    """Contexto de arranque del dashboard.

    Nota: La lógica completa (operativa activa vs histórico) se implementará
    según docs/01-flujo_inicio_dashboard.md y docs/02-guia_dashboard_backstage.md.
    """

    mode: str  # "realtime" | "historical"
    message: str


def determine_startup_context() -> StartupContext:
    """Determina el contexto operativo inicial.

    Placeholder en fase inicial: por ahora no consulta DB.
    """

    return StartupContext(mode="realtime", message="Contexto inicial pendiente de implementación")
