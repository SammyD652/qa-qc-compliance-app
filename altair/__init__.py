"""Stub altair module to satisfy Streamlit dependency when altair is not installed."""

class _Chart:
    def __init__(self, *args, **kwargs):
        pass

    def mark_point(self, *args, **kwargs):
        return self

    def encode(self, *args, **kwargs):
        return self


def Chart(*args, **kwargs):
    """Return a stub Chart object."""
    return _Chart(*args, **kwargs)
