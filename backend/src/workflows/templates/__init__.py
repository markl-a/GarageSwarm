"""
Workflow Template System

Provides template loading, parsing, and validation for YAML-based workflow definitions.

Components:
- TemplateLoader: Discovers and loads templates from the templates directory
- TemplateMetadata: Metadata model for template information
- Template validation utilities
"""

from .loader import (
    TemplateLoader,
    TemplateMetadata,
    TemplateValidationError,
)

__all__ = [
    "TemplateLoader",
    "TemplateMetadata",
    "TemplateValidationError",
]
