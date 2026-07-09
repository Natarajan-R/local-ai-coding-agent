"""Optional web server: a local dashboard that streams the agent's run.

Requires the ``[web]`` extra (aiohttp). Imported lazily by the CLI so the core
package has no hard dependency on it.
"""
from .broadcaster import ApprovalBroker, Broadcaster

__all__ = ["Broadcaster", "ApprovalBroker"]
