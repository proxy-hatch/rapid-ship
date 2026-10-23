"""Report a problem the user can fix: what is wrong, then what to do next."""


class UsageError(Exception):
    """A problem the user can fix, such as a bad setting or an unknown input value.

    When an exception found the problem, raise this from it: `raise UsageError(...) from
    error`. The traceback then keeps the cause. Catch it only in the entry point, which
    writes its text to stderr and exits 1.
    """

    def __init__(self, problem: str, next_step: str) -> None:
        super().__init__(f"{problem}; {next_step}")
        self.problem = problem
        self.next_step = next_step
