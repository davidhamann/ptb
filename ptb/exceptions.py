class PtbException(Exception):
    """Base exception."""


class PtbProcessException(PtbException):
    """Raised when external process fails."""
