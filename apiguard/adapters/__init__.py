"""Adapters for different HTTP clients."""

from apiguard.adapters.httpx import AsyncRateLimitedClient

__all__ = ["AsyncRateLimitedClient"]
