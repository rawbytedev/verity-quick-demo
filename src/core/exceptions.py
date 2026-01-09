"""
Unified exception hierarchy for Verity operations.
All Verity-specific exceptions inherit from VerityError.
"""
class VerityError(Exception):
    """Base exception for all Verity operations."""

class VerityBackendError(VerityError):
    """Backend operation failed (accounts, sessions, DID documents)."""

class VerityCliError(VerityError):
    """CLI operation or user input validation failed."""

class VerityClaimError(VerityError):
    """Claim creation, signing, or validation failed."""

class VerityVerifierError(VerityError):
    """Verification operation failed."""

class VerityMiddlewareError(VerityError):
    """Middleware communication or HTTP operation failed."""

class VerityStorageError(VerityError):
    """Storage backend operation failed (database, IPFS mock)."""

class VerityCryptoError(VerityError):
    """Cryptographic operation failed."""

class VerityValidationError(VerityError):
    """Validation of data (DID format, input, etc.) failed."""
