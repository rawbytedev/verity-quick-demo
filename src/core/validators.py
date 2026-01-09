"""
DID format validation and utilities.
Supports did:verity format: did:verity:<namespace>:<entity-identifier>
"""
import re
from typing import Optional
from .exceptions import VerityValidationError

## Needs to be fully tested
class DIDValidator:
    """Validates DID format and structure."""

    # DID format: did:verity:{namespace}:{entity}
    # Namespaces: gov, org, media, edu, ind
    # Entity: lowercase alphanumeric and hyphens
    DID_PATTERN = r"^did:verity:(gov|org|media|edu|ind):[a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?$"

    VALID_NAMESPACES = {"gov", "org", "media", "edu", "ind"}

    @staticmethod
    def validate(did: str) -> bool:
        """
        Check if DID matches the required format.

        Args:
            did: Full DID string to validate.

        Returns:
            True if valid, False otherwise.
        """
        if not isinstance(did, str):
            return False
        return bool(re.match(DIDValidator.DID_PATTERN, did, re.IGNORECASE))

    @staticmethod
    def validate_or_raise(did: str) -> str:
        """
        Validate DID and raise exception if invalid.

        Args:
            did: Full DID string to validate.

        Returns:
            The DID string if valid.

        Raises:
            VerityValidationError: If DID format is invalid.
        """
        if not DIDValidator.validate(did):
            raise VerityValidationError(
                f"Invalid DID format: {did}. "
                f"Expected: did:verity:<namespace>:<entity>\n"
                f"Valid namespaces: {', '.join(DIDValidator.VALID_NAMESPACES)}"
            )
        return did

    @staticmethod
    def extract_parts(did: str) -> Optional[dict]:
        """
        Extract components from a valid DID.

        Args:
            did: Full DID string.

        Returns:
            Dict with 'namespace' and 'entity' keys, or None if invalid.
        """
        match = re.match(DIDValidator.DID_PATTERN, did, re.IGNORECASE)
        if not match:
            return None
        return {"namespace": match.group(1).lower(), "entity": match.group(2).lower()}

    @staticmethod
    def is_valid_namespace(namespace: str) -> bool:
        """
        Check if namespace is valid.

        Args:
            namespace: Namespace to check.

        Returns:
            True if valid namespace.
        """
        return namespace.lower() in DIDValidator.VALID_NAMESPACES

    @staticmethod
    def is_valid_entity(entity: str) -> bool:
        """
        Check if entity identifier is valid format.

        Args:
            entity: Entity identifier to check.

        Returns:
            True if valid format (lowercase alphanumeric and hyphens).
        """
        if not isinstance(entity, str) or not entity:
            return False
        return bool(re.match(r"^[a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?$", entity))
