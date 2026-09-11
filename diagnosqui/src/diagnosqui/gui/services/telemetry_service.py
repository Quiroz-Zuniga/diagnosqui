"""Una instancia de muestreo, conservada en el pool de telemetría de un hilo."""

from __future__ import annotations
from typing import Any, Optional
from diagnosqui.core.telemetry import SystemSampler


class TelemetryService:
    def __init__(self) -> None:
        self.sampler: Optional[SystemSampler] = None

    def sample(self, processes: bool = True) -> dict[str, Any]:
        if self.sampler is None:
            self.sampler = SystemSampler()
        result: dict[str, Any] = {"performance": self.sampler.sample_performance()}
        if processes:
            result["processes"] = self.sampler.read_processes()
        return result
