"""Exceptions for Reolink ISP."""

from __future__ import annotations


class ReolinkIspError(Exception):
    """Base integration error."""


class CannotConnect(ReolinkIspError):
    """Raised when the camera cannot be reached."""


class InvalidAuth(ReolinkIspError):
    """Raised when authentication fails."""


class InvalidResponse(ReolinkIspError):
    """Raised when the camera returns an unexpected response."""
