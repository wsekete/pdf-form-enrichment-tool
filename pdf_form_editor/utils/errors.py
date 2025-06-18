"""Custom exceptions for PDF Form Enrichment Tool."""


class PDFProcessingError(Exception):
    """Base exception for PDF processing errors."""

    pass


class ValidationError(PDFProcessingError):
    """Raised when validation fails."""

    pass


class BEMNamingError(PDFProcessingError):
    """Raised when BEM naming fails."""

    pass


class AIServiceError(PDFProcessingError):
    """Raised when AI service calls fail."""

    pass


class ConfigurationError(Exception):
    """Raised when configuration is invalid."""

    pass
