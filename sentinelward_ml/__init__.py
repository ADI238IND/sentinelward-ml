"""Research inference adapters and a conservative live-contract bridge."""

__all__ = ["SentinelWardModels", "SentinelWardDriftMonitor", "build_research_verdict"]


def __getattr__(name):
    if name == "SentinelWardModels":
        from .inference import SentinelWardModels
        return SentinelWardModels
    if name == "SentinelWardDriftMonitor":
        from .drift import SentinelWardDriftMonitor
        return SentinelWardDriftMonitor
    if name == "build_research_verdict":
        from .live_contract import build_research_verdict
        return build_research_verdict
    raise AttributeError(name)
