"""BlendGuard backend.

Four independent layers (see docs/architecture.md):

    DATA (providers) -> MODEL -> OPTIMIZER -> PRESENTATION (api)

Dependencies must only ever point downward in that chain.
"""

__version__ = "0.1.0"
