"""
BEM Naming Rules Engine

Implements core BEM naming logic and validation according to the original task specification.
This replaces the basic rule-based approach with a comprehensive engine that handles:
- Block, element, modifier pattern recognition
- Naming convention validation and compliance checking
- Special case handling (radio groups, signatures, custom fields)
- Name uniqueness checking within document scope
- BEM pattern templates and examples
- Name generation confidence scoring
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from ..core.field_extractor import FormField, FieldType
from ..training.data_loader import FieldContext
from ..utils.logging import get_logger

logger = get_logger(__name__)


class BEMComponentType(Enum):
    """BEM component types"""
    BLOCK = "block"
    ELEMENT = "element"
    MODIFIER = "modifier"


@dataclass
class BEMValidationResult:
    """Result of BEM validation"""
    is_valid: bool
    error_message: Optional[str] = None
    suggestions: List[str] = None
    confidence: float = 0.0


@dataclass
class BEMNameCandidate:
    """A candidate BEM name with metadata"""
    name: str
    confidence: float
    rationale: str
    components: Dict[str, str]
    rule_applied: str


class SpecialCaseType(Enum):
    """Special field types requiring custom handling"""
    RADIO_GROUP = "radio_group"
    RADIO_BUTTON = "radio_button"
    SIGNATURE = "signature"
    CUSTOM_FIELD = "custom_field"
    GROUPED_FIELD = "grouped_field"


class BEMNamingEngine:
    """
    Core BEM naming logic and validation engine.
    
    Implements the formal BEM (Block Element Modifier) naming convention:
    - Format: block_element__modifier
    - Example: owner-information_name__first
    """
    
    def __init__(self):
        self.bem_patterns = self._load_bem_patterns()
        self.reserved_words = self._load_reserved_words()
        self.special_rules = self._load_special_rules()
        
    def _load_bem_patterns(self) -> Dict[str, str]:
        """Load BEM pattern templates"""
        return {
            "owner_info": "owner-information",
            "contact": "contact-details", 
            "payment": "payment-information",
            "insurance": "insurance-details",
            "vehicle": "vehicle-information",
            "driver": "driver-details",
            "medical": "medical-information",
            "employment": "employment-details",
            "financial": "financial-information",
            "signature": "signature-section",
            "date": "date-field",
            "checkbox": "checkbox-option",
            "radio": "radio-selection"
        }
    
    def _load_reserved_words(self) -> List[str]:
        """Load reserved words that cannot be used in BEM names"""
        return [
            "group", "custom", "temp", "field", "form", "input",
            "element", "widget", "control", "button", "text"
        ]
    
    def _load_special_rules(self) -> Dict[SpecialCaseType, Dict[str, Any]]:
        """Load special case handling rules"""
        return {
            SpecialCaseType.RADIO_GROUP: {
                "pattern": "{section}_{topic}__group",
                "element_pattern": "{section}_{topic}__option",
                "requires_grouping": True
            },
            SpecialCaseType.RADIO_BUTTON: {
                "pattern": "{section}_{topic}__option-{value}",
                "parent_reference": True
            },
            SpecialCaseType.SIGNATURE: {
                "pattern": "{section}_signature__field",
                "modifier_options": ["field", "date", "witness"]
            },
            SpecialCaseType.CUSTOM_FIELD: {
                "pattern": "{section}_{purpose}__custom",
                "validation_required": True
            },
            SpecialCaseType.GROUPED_FIELD: {
                "pattern": "{group}_{element}__modifier",
                "hierarchy_aware": True
            }
        }
    
    def validate_bem_name(self, name: str) -> BEMValidationResult:
        """
        Validate a BEM name according to formal conventions.
        
        Args:
            name: The BEM name to validate
            
        Returns:
            BEMValidationResult with validation status and suggestions
        """
        if not name:
            return BEMValidationResult(
                is_valid=False,
                error_message="BEM name cannot be empty",
                suggestions=["Provide a valid BEM name"]
            )
        
        # Check basic BEM format: block_element__modifier
        bem_pattern = r'^[a-z0-9-]+_[a-z0-9-]+(?:__[a-z0-9-]+)?$'
        if not re.match(bem_pattern, name):
            return BEMValidationResult(
                is_valid=False,
                error_message="Invalid BEM format. Expected: block_element__modifier",
                suggestions=[
                    "Use lowercase letters, numbers, and hyphens only",
                    "Format: block_element__modifier",
                    "Example: owner-information_name__first"
                ]
            )
        
        # Check for reserved words
        parts = self._parse_bem_components(name)
        for component, value in parts.items():
            if any(reserved in value for reserved in self.reserved_words):
                return BEMValidationResult(
                    is_valid=False,
                    error_message=f"Reserved word found in {component}: {value}",
                    suggestions=[f"Replace reserved word in {component}"]
                )
        
        # Check length constraints
        if len(name) > 50:
            return BEMValidationResult(
                is_valid=False,
                error_message="BEM name too long (max 50 characters)",
                suggestions=["Shorten the name while maintaining clarity"]
            )
        
        # Calculate confidence based on pattern compliance
        confidence = self._calculate_validation_confidence(name, parts)
        
        return BEMValidationResult(
            is_valid=True,
            confidence=confidence
        )
    
    def generate_bem_candidates(self, field: FormField, context: FieldContext) -> List[BEMNameCandidate]:
        """
        Generate multiple BEM name candidates for a field.
        
        Args:
            field: The form field to name
            context: Extracted context information
            
        Returns:
            List of BEM name candidates sorted by confidence
        """
        candidates = []
        
        # Apply pattern-based generation
        pattern_candidates = self._generate_pattern_candidates(field, context)
        candidates.extend(pattern_candidates)
        
        # Apply context-based generation
        context_candidates = self._generate_context_candidates(field, context)
        candidates.extend(context_candidates)
        
        # Apply special case rules
        special_candidates = self._apply_special_rules(field, context)
        candidates.extend(special_candidates)
        
        # Sort by confidence and remove duplicates
        unique_candidates = self._deduplicate_candidates(candidates)
        return sorted(unique_candidates, key=lambda c: c.confidence, reverse=True)
    
    def check_name_uniqueness(self, name: str, existing_names: List[str]) -> bool:
        """
        Check if a BEM name is unique within the document scope.
        
        Args:
            name: The BEM name to check
            existing_names: List of existing field names in the document
            
        Returns:
            True if name is unique, False otherwise
        """
        return name not in existing_names
    
    def apply_special_rules(self, field: FormField, context: FieldContext) -> Optional[str]:
        """
        Apply special case handling rules for specific field types.
        
        Args:
            field: The form field
            context: Field context information
            
        Returns:
            Special rule BEM name if applicable, None otherwise
        """
        special_type = self._identify_special_case(field, context)
        if not special_type:
            return None
        
        rules = self.special_rules.get(special_type)
        if not rules:
            return None
        
        return self._apply_special_rule_pattern(field, context, special_type, rules)
    
    def _parse_bem_components(self, bem_name: str) -> Dict[str, str]:
        """Parse BEM name into components"""
        parts = {}
        
        if '__' in bem_name:
            block_element, modifier = bem_name.split('__', 1)
            parts['modifier'] = modifier
        else:
            block_element = bem_name
        
        if '_' in block_element:
            block, element = block_element.split('_', 1)
            parts['block'] = block
            parts['element'] = element
        else:
            parts['block'] = block_element
        
        return parts
    
    def _calculate_validation_confidence(self, name: str, components: Dict[str, str]) -> float:
        """Calculate confidence score for BEM validation"""
        confidence = 0.0
        
        # Base score for valid format
        confidence += 0.3
        
        # Bonus for proper component structure
        if 'block' in components and 'element' in components:
            confidence += 0.3
        
        # Bonus for meaningful names (not generic)
        if all(len(comp) > 2 for comp in components.values()):
            confidence += 0.2
        
        # Bonus for recognized patterns
        block = components.get('block', '')
        if any(pattern in block for pattern in self.bem_patterns.values()):
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def _generate_pattern_candidates(self, field: FormField, context: FieldContext) -> List[BEMNameCandidate]:
        """Generate candidates based on known patterns"""
        candidates = []
        
        # Try to match section to known patterns
        section = self._extract_section_from_context(context)
        element = self._extract_element_from_context(field, context)
        
        for pattern_key, pattern_block in self.bem_patterns.items():
            if pattern_key in section.lower():
                bem_name = f"{pattern_block}_{element}"
                
                # Add modifier if field type suggests it
                modifier = self._suggest_modifier_for_field(field)
                if modifier:
                    bem_name += f"__{modifier}"
                
                candidates.append(BEMNameCandidate(
                    name=bem_name,
                    confidence=0.8,
                    rationale=f"Matched pattern '{pattern_key}' from section context",
                    components=self._parse_bem_components(bem_name),
                    rule_applied="pattern_matching"
                ))
        
        return candidates
    
    def _generate_context_candidates(self, field: FormField, context: FieldContext) -> List[BEMNameCandidate]:
        """Generate candidates based on extracted context"""
        candidates = []
        
        if not context.nearby_text:
            return candidates
        
        # Extract meaningful words from context
        context_words = self._extract_meaningful_words(context.nearby_text)
        
        if len(context_words) >= 2:
            block = self._normalize_for_bem(context_words[0])
            element = self._normalize_for_bem(context_words[1])
            
            bem_name = f"{block}_{element}"
            
            # Add field type modifier
            if field.field_type == FieldType.TEXT:
                bem_name += "__input"
            elif field.field_type == FieldType.CHECKBOX:
                bem_name += "__option"
            elif field.field_type == FieldType.SIGNATURE:
                bem_name += "__field"
            
            candidates.append(BEMNameCandidate(
                name=bem_name,
                confidence=0.6,
                rationale=f"Generated from context words: {', '.join(context_words)}",
                components=self._parse_bem_components(bem_name),
                rule_applied="context_extraction"
            ))
        
        return candidates
    
    def _apply_special_rules(self, field: FormField, context: FieldContext) -> List[BEMNameCandidate]:
        """Apply special case rules and return candidates"""
        candidates = []
        
        special_type = self._identify_special_case(field, context)
        if special_type:
            special_name = self._apply_special_rule_pattern(field, context, special_type, self.special_rules[special_type])
            if special_name:
                candidates.append(BEMNameCandidate(
                    name=special_name,
                    confidence=0.9,
                    rationale=f"Applied special rule for {special_type.value}",
                    components=self._parse_bem_components(special_name),
                    rule_applied=f"special_{special_type.value}"
                ))
        
        return candidates
    
    def _identify_special_case(self, field: FormField, context: FieldContext) -> Optional[SpecialCaseType]:
        """Identify if field requires special case handling"""
        
        # Check for radio group
        if field.field_type == FieldType.RADIO and "group" in field.name.lower():
            return SpecialCaseType.RADIO_GROUP
        elif field.field_type == FieldType.RADIO:
            return SpecialCaseType.RADIO_BUTTON
        
        # Check for signature
        if field.field_type == FieldType.SIGNATURE:
            return SpecialCaseType.SIGNATURE
        
        # Check for grouped fields (parent-child relationships)
        if field.parent_field_id:
            return SpecialCaseType.GROUPED_FIELD
        
        return None
    
    def _apply_special_rule_pattern(self, field: FormField, context: FieldContext, 
                                  special_type: SpecialCaseType, rules: Dict[str, Any]) -> Optional[str]:
        """Apply specific special rule pattern"""
        pattern = rules.get("pattern", "")
        
        if special_type == SpecialCaseType.RADIO_GROUP:
            section = self._extract_section_from_context(context)
            topic = self._extract_element_from_context(field, context)
            return pattern.format(section=section, topic=topic)
        
        elif special_type == SpecialCaseType.RADIO_BUTTON:
            section = self._extract_section_from_context(context)
            topic = self._extract_element_from_context(field, context)
            value = self._extract_radio_value(field)
            return pattern.format(section=section, topic=topic, value=value)
        
        elif special_type == SpecialCaseType.SIGNATURE:
            section = self._extract_section_from_context(context)
            return pattern.format(section=section)
        
        elif special_type == SpecialCaseType.GROUPED_FIELD:
            group = self._extract_group_name(field, context)
            element = self._extract_element_from_context(field, context)
            modifier = self._suggest_modifier_for_field(field)
            return pattern.format(group=group, element=element, modifier=modifier)
        
        return None
    
    def _extract_section_from_context(self, context: FieldContext) -> str:
        """Extract section name from context"""
        if context.section_header:
            return self._normalize_for_bem(context.section_header)
        
        # Try to infer from nearby text
        if context.nearby_text:
            for text in context.nearby_text:
                if len(text) > 10 and any(word in text.lower() for word in ["section", "part", "information"]):
                    return self._normalize_for_bem(text.split()[0])
        
        return "general"
    
    def _extract_element_from_context(self, field: FormField, context: FieldContext) -> str:
        """Extract element name from field and context"""
        if context.label:
            return self._normalize_for_bem(context.label)
        
        # Clean field name
        clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', field.name)
        if clean_name and not clean_name.lower().startswith(('field', 'text', 'input')):
            return self._normalize_for_bem(clean_name)
        
        return "field"
    
    def _suggest_modifier_for_field(self, field: FormField) -> Optional[str]:
        """Suggest appropriate modifier based on field type"""
        modifiers = {
            FieldType.TEXT: "input",
            FieldType.CHECKBOX: "option", 
            FieldType.RADIO: "selection",
            FieldType.SIGNATURE: "field",
            FieldType.DROPDOWN: "choice"
        }
        return modifiers.get(field.field_type)
    
    def _extract_meaningful_words(self, text_list: List[str]) -> List[str]:
        """Extract meaningful words from context text"""
        meaningful_words = []
        
        for text in text_list:
            words = re.findall(r'\b[a-zA-Z]{3,}\b', text)
            for word in words:
                if word.lower() not in ['the', 'and', 'for', 'with', 'this', 'that', 'field', 'name']:
                    meaningful_words.append(word)
        
        return meaningful_words[:3]  # Limit to first 3 meaningful words
    
    def _normalize_for_bem(self, text: str) -> str:
        """Normalize text for BEM component usage"""
        # Convert to lowercase and replace spaces with hyphens
        normalized = re.sub(r'[^a-zA-Z0-9\s]', '', text.lower())
        normalized = re.sub(r'\s+', '-', normalized.strip())
        
        # Remove common prefixes/suffixes
        normalized = re.sub(r'^(field|input|text|control)-?', '', normalized)
        normalized = re.sub(r'-?(field|input|text|control)$', '', normalized)
        
        return normalized or "field"
    
    def _extract_radio_value(self, field: FormField) -> str:
        """Extract value identifier from radio button field"""
        if hasattr(field, 'export_value') and field.export_value:
            return self._normalize_for_bem(str(field.export_value))
        
        # Use last part of field name
        name_parts = field.name.split('.')
        if len(name_parts) > 1:
            return self._normalize_for_bem(name_parts[-1])
        
        return "option"
    
    def _extract_group_name(self, field: FormField, context: FieldContext) -> str:
        """Extract group name for grouped fields"""
        if field.parent_field_id and context.visual_group:
            return self._normalize_for_bem(context.visual_group)
        
        return self._extract_section_from_context(context)
    
    def _deduplicate_candidates(self, candidates: List[BEMNameCandidate]) -> List[BEMNameCandidate]:
        """Remove duplicate candidates, keeping highest confidence"""
        seen_names = {}
        unique_candidates = []
        
        for candidate in candidates:
            if candidate.name not in seen_names or candidate.confidence > seen_names[candidate.name].confidence:
                seen_names[candidate.name] = candidate
        
        return list(seen_names.values())