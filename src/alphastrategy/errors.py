class ImportRejected(ValueError):
    """Fail-closed import. str(e) is shown in CLI and Web."""


class IllegalWeights(ValueError):
    """DSL output failed long-only / finite / sum-to-1 checks."""


class HaltRequested(Exception):
    """Health halt: no new orders, do not flatten."""


class FlattenRequested(Exception):
    def __init__(self, scope: str):
        super().__init__(scope)
        self.scope = scope
