from __future__ import annotations


class BizWatcherError(Exception):
    pass


class TestNotFoundError(BizWatcherError):
    pass


class RunNotFoundError(BizWatcherError):
    pass


class ProviderError(BizWatcherError):
    pass


class OllamaConnectionError(ProviderError):
    pass


class JudgeParseError(BizWatcherError):
    pass


class DuplicateTestIdError(BizWatcherError):
    pass
