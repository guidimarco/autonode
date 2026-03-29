"""Core domain exceptions shared across layers."""


class TokenBudgetExceededError(RuntimeError):
    """Raised when cumulative token usage exceeds the configured workflow budget."""

    def __init__(self, total_tokens: int, budget: int) -> None:
        self.total_tokens = total_tokens
        self.budget = budget
        super().__init__(f"Token budget exceeded: total_tokens={total_tokens} budget={budget}")
