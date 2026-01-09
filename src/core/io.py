"""
Shared console I/O wrapper for both CLI and internal logging.
"""
class ConsoleIO:
    """wrapper around input/print"""

    def input(self, prompt: str = "") -> str:
        """
        Read a string from standard input.
        The trailing newline is stripped.

        Args:
            prompt: String to print before reading input.

        Returns:
            User input as string.
        """
        return input(prompt)

    def print(self, *args, **kwargs) -> None:
        """
        Print values to stdout.

        Args:
            *args: Values to print.
            **kwargs: Keyword arguments passed to print().
        """
        print(*args, **kwargs)
