"""Configuration constants for PDF form processing."""

# Field Extraction Constants
class FieldExtractionConstants:
    """Constants for field extraction and processing."""
    
    # Form size thresholds
    LARGE_FORM_THRESHOLD = 1000  # Warning threshold for large forms
    
    # Spatial analysis
    PROXIMITY_THRESHOLD = 100  # Pixels for nearby text detection
    MAX_NEARBY_TEXT = 10  # Maximum number of nearby text elements to consider
    
    # Field dimensions
    DEFAULT_FIELD_WIDTH = 0.0
    DEFAULT_FIELD_HEIGHT = 0.0
    
    # Field naming
    MAX_FIELD_NAME_LENGTH = 255  # Maximum length for field names
    
    # Context extraction
    CONTEXT_CONFIDENCE_BASE = 0.3  # Base confidence for context extraction
    LABEL_CONFIDENCE_BOOST = 0.3  # Boost for clear labels
    NEARBY_TEXT_CONFIDENCE_BOOST = 0.2  # Boost for substantial nearby text
    SECTION_HEADER_CONFIDENCE_BOOST = 0.1  # Boost for section headers
    DIRECTIONAL_TEXT_CONFIDENCE_BOOST = 0.1  # Boost for directional text


# Training Data Constants  
class TrainingConstants:
    """Constants for training data processing."""
    
    # Spatial correlation
    SPATIAL_CORRELATION_THRESHOLD = 50  # Maximum distance for field correlation
    
    # Confidence calculation weights
    CORRELATION_RATIO_WEIGHT = 0.7  # Weight for correlation ratio in confidence
    COUNT_SIMILARITY_WEIGHT = 0.3  # Weight for field count similarity
    
    # BEM validation
    MAX_BEM_NAME_LENGTH = 50  # Maximum length for BEM names
    
    # Pattern analysis
    MIN_PATTERN_FREQUENCY = 2  # Minimum frequency for pattern recognition
    MAX_CONTEXT_TRIGGERS = 5  # Maximum context triggers per pattern
    
    # Similarity matching weights
    TEXT_SIMILARITY_WEIGHT = 0.35
    SPATIAL_SIMILARITY_WEIGHT = 0.20
    TYPE_SIMILARITY_WEIGHT = 0.15
    CONTEXT_SIMILARITY_WEIGHT = 0.20
    VISUAL_SIMILARITY_WEIGHT = 0.10


# PDF Processing Constants
class PDFConstants:
    """Constants for PDF document processing."""
    
    # Page layout
    APPROXIMATE_LINE_HEIGHT = 12  # Points
    APPROXIMATE_CHAR_WIDTH = 6  # Points
    DEFAULT_LEFT_MARGIN = 100  # Points
    DEFAULT_TOP_MARGIN = 800  # Points (from bottom)
    LINE_SPACING = 15  # Points between lines
    
    # Visual grouping thresholds (Y coordinates)
    HEADER_SECTION_THRESHOLD = 700
    UPPER_SECTION_THRESHOLD = 500
    MIDDLE_SECTION_THRESHOLD = 300
    LOWER_SECTION_THRESHOLD = 100
    
    # Field type flags (from PDF specification)
    READONLY_FLAG = 1  # Bit 1
    REQUIRED_FLAG = 2  # Bit 2
    NO_EXPORT_FLAG = 4  # Bit 3
    MULTILINE_FLAG = 4096  # Bit 13
    PASSWORD_FLAG = 8192  # Bit 14
    PUSHBUTTON_FLAG = 16384  # Bit 15
    RADIO_FLAG = 32768  # Bit 16
    COMBO_FLAG = 131072  # Bit 18


# Error Handling Constants
class ErrorConstants:
    """Constants for error handling and validation."""
    
    # Validation thresholds
    MIN_CONFIDENCE_THRESHOLD = 0.5  # Minimum confidence for training pairs
    
    # Retry and timeout
    MAX_RETRY_ATTEMPTS = 3
    DEFAULT_TIMEOUT_MS = 120000  # 2 minutes
    
    # Cache limits
    MAX_CACHE_SIZE = 1000  # Maximum cached items
    CACHE_CLEANUP_THRESHOLD = 800  # When to start cleanup