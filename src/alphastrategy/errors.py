class ImportRejected(ValueError):
    """Fail-closed import. str(e) is shown in CLI and Web."""

    def __init__(self, message: str, kind: str = "unknown") -> None:
        super().__init__(message)
        self.kind = kind


class IllegalWeights(ValueError):
    """DSL output failed long-only / finite / sum-to-1 checks."""


class HaltRequested(Exception):
    """Health halt: no new orders, do not flatten."""


class FlattenRequested(Exception):
    def __init__(self, scope: str, reason: str = "limit"):
        super().__init__(scope)
        self.scope = scope
        self.reason = reason
