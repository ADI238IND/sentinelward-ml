"""Research inference adapters and a conservative live-contract bridge."""

__all__ = ["SentinelWardModels", "SentinelWardDriftMonitor",
           "build_research_verdict", "VitalsWindowAssembler", "validate_m5_event"]


def __getattr__(name):
    # The schema validator uses only the standard library; keep it usable for
    # integration checks before scientific model dependencies are installed.
    if name == "SentinelWardModels":
        from .inference import SentinelWardModels
        return SentinelWardModels
    if name == "SentinelWardDriftMonitor":
        from .drift import SentinelWardDriftMonitor
        return SentinelWardDriftMonitor
    if name == "build_research_verdict":
        from .live_contract import build_research_verdict
        return build_research_verdict
    if name == "VitalsWindowAssembler":
        from .windows import VitalsWindowAssembler
        return VitalsWindowAssembler
    if name == "validate_m5_event":
        from .m5_external import validate_m5_event
        return validate_m5_event
    raise AttributeError(name)
