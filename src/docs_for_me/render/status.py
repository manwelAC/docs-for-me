import time
from dataclasses import dataclass, field

import typer


@dataclass
class StatusReporter:
    quiet: bool = False
    _started_at: float = field(default_factory=time.perf_counter)

    def step(self, message: str) -> None:
        if self.quiet:
            return

        elapsed = time.perf_counter() - self._started_at
        typer.echo(f"[{elapsed:5.1f}s] {message}", err=True)

    def done(self, message: str = "Done.") -> None:
        self.step(message)
