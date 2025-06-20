"""
Preservation Mode BEM Generator

Intelligently preserves good existing field names while making minimal improvements.
Uses training data to learn from existing good patterns and only suggests changes
when there are clear improvements to be made.
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Set
from enum import Enum

from ..core.field_extractor import FormField, FieldContext
from ..training.data_loader import CSVFieldMapping
from ..utils.logging import get_logger

logger = get_logger(__name__)


class PreservationAction(Enum):
    """Actions that preservation mode can take."""
    PRESERVE = "preserve"        # Keep the existing name
    IMPROVE = "improve"          # Make a minor improvement
    RESTRUCTURE = "restructure"  # Significant structural change needed


@dataclass
class PreservationAnalysis:
    """Analysis of whether to preserve or improve a field name."""
    current_name: str
    suggested_name: str
    action: PreservationAction
    confidence: float
    reasoning: str
    improvements: List[str]
    

class PreservationBEMGenerator:
    """Generate BEM names with intelligent preservation of good existing names."""
    
    def __init__(self, training_examples: List[CSVFieldMapping]):
        """Initialize with training data for pattern learning."""
        self.training_examples = training_examples
        self.bem_pattern = re.compile(
            r'^[a-z][a-z0-9]*(-[a-z0-9]+)*(_[a-z][a-z0-9]*(-[a-z0-9]+)*)?(--[a-z][a-z0-9]*(-[a-z0-9]+)*)?$'
        )
        self.good_patterns = self._analyze_good_patterns()
        
        logger.info(f"PreservationBEMGenerator initialized with {len(training_examples)} examples")
        logger.info(f"Identified {len(self.good_patterns.get('blocks', {}))} unique blocks, "
                   f"{len(self.good_patterns.get('structures', []))} good structures")
    
    def analyze_field_name(self, field: FormField, context: FieldContext) -> PreservationAnalysis:
        """
        Analyze if a field name should be preserved, improved, or restructured.
        
        Args:
            field: Form field with current name
            context: Field context information
            
        Returns:
            PreservationAnalysis with recommended action
        """
        current_name = field.name
        logger.debug(f"Analyzing field name: {current_name}")
        
        # Step 1: Check if current name is already good
        if self._is_good_bem_name(current_name):
            return PreservationAnalysis(
                current_name=current_name,
                suggested_name=current_name,
                action=PreservationAction.PRESERVE,
                confidence=0.9,
                reasoning="Current name follows good BEM conventions",
                improvements=[]
            )
        
        # Step 2: Check if minor improvements can fix it
        improved_name = self._try_minor_improvements(current_name, field, context)
        if improved_name and improved_name != current_name:
            improvements = self._identify_improvements(current_name, improved_name)
            return PreservationAnalysis(
                current_name=current_name,
                suggested_name=improved_name,
                action=PreservationAction.IMPROVE,
                confidence=0.7,
                reasoning=f"Minor improvements: {', '.join(improvements)}",
                improvements=improvements
            )
        
        # Step 3: Determine if major restructuring is needed
        restructured_name = self._generate_bem_from_context(field, context)
        if restructured_name:
            return PreservationAnalysis(
                current_name=current_name,
                suggested_name=restructured_name,
                action=PreservationAction.RESTRUCTURE,
                confidence=0.5,
                reasoning="Current name needs significant restructuring for BEM compliance",
                improvements=["restructure_to_bem"]
            )
        
        # Step 4: Fall back to preservation if nothing better found
        return PreservationAnalysis(
            current_name=current_name,
            suggested_name=current_name,
            action=PreservationAction.PRESERVE,
            confidence=0.3,
            reasoning="Unable to find clear improvements, preserving existing name",
            improvements=[]
        )
    
    def _analyze_good_patterns(self) -> Dict[str, List[str]]:
        """Analyze training data to identify good naming patterns."""
        patterns = {
            'blocks': {},
            'elements': {},
            'structures': []
        }
        
        # Limit processing to avoid performance issues
        max_examples = min(1000, len(self.training_examples))
        logger.debug(f"Processing {max_examples} training examples for patterns")
        
        for example in self.training_examples[:max_examples]:
            api_name = example.api_name
            if not api_name:
                continue
                
            # Quick BEM check instead of full validation
            if '_' in api_name or '-' in api_name:
                # Parse BEM structure
                parts = self._parse_bem_name(api_name)
                if parts:
                    block, element, modifier = parts
                    
                    # Collect block patterns
                    if block not in patterns['blocks']:
                        patterns['blocks'][block] = []
                    patterns['blocks'][block].append(api_name)
                    
                    # Collect element patterns
                    if element and element not in patterns['elements']:
                        patterns['elements'][element] = []
                    if element:
                        patterns['elements'][element].append(api_name)
                    
                    # Store complete structures
                    patterns['structures'].append(api_name)
        
        logger.debug(f"Found {len(patterns['blocks'])} unique blocks, "
                    f"{len(patterns['elements'])} unique elements")
        return patterns
    
    def _is_good_bem_name(self, name: str) -> bool:
        """Check if a name follows good BEM conventions."""
        if not name:
            return False
        
        # Check basic BEM syntax
        if not self.bem_pattern.match(name):
            return False
        
        # Check for common anti-patterns
        anti_patterns = [
            r'field-field',  # Redundant field references
            r'__\d+$',       # Ending with just numbers
            r'^general_',    # Generic naming
            r'__{2,}',       # Multiple consecutive modifiers
        ]
        
        for pattern in anti_patterns:
            if re.search(pattern, name):
                return False
        
        # Check if it matches known good patterns
        for good_name in self.good_patterns.get('structures', []):
            if self._names_are_similar(name, good_name):
                return True
        
        return True
    
    def _try_minor_improvements(self, current_name: str, field: FormField, context: FieldContext) -> Optional[str]:
        """Try to make minor improvements to the current name."""
        improved = current_name
        
        # Fix common issues
        improvements = []
        
        # 1. Fix hyphen/underscore usage
        if '--' in improved and '_' not in improved:
            # Convert double hyphen to underscore for element separation
            parts = improved.split('--')
            if len(parts) == 2:
                improved = f"{parts[0]}_{parts[1]}"
                improvements.append("fix_element_separator")
        
        # 2. Standardize block names based on training data
        parts = self._parse_bem_name(improved)
        if parts:
            block, element, modifier = parts
            
            # Look for better block names in training data
            better_block = self._find_better_block(block, context)
            if better_block and better_block != block:
                improved = improved.replace(block, better_block, 1)
                improvements.append("improve_block_name")
        
        # 3. Fix casing issues
        if improved != improved.lower():
            improved = improved.lower()
            improvements.append("fix_casing")
        
        # 4. Remove redundant parts
        redundant_patterns = [
            (r'field-field', 'field'),
            (r'_field$', ''),
            (r'^form-', ''),
        ]
        
        for pattern, replacement in redundant_patterns:
            if re.search(pattern, improved):
                improved = re.sub(pattern, replacement, improved)
                improvements.append("remove_redundancy")
        
        return improved if improvements else None
    
    def _generate_bem_from_context(self, field: FormField, context: FieldContext) -> Optional[str]:
        """Generate a new BEM name based on field context and training patterns."""
        # Analyze context to determine appropriate block
        block = self._infer_block_from_context(context)
        element = self._infer_element_from_field(field)
        
        if not block or not element:
            return None
        
        # Construct BEM name
        bem_name = f"{block}_{element}"
        
        # Add modifier if needed
        modifier = self._infer_modifier_from_context(context)
        if modifier:
            bem_name += f"__{modifier}"
        
        return bem_name
    
    def _parse_bem_name(self, name: str) -> Optional[Tuple[str, Optional[str], Optional[str]]]:
        """Parse a BEM name into block, element, modifier components."""
        try:
            # Handle modifiers first (__)
            parts = name.split('__')
            base = parts[0]
            modifier = parts[1] if len(parts) > 1 else None
            
            # Handle block_element structure
            if '_' in base:
                base_parts = base.split('_')
                block = '_'.join(base_parts[:-1])  # Everything except last part
                element = base_parts[-1]          # Last part
            else:
                block = base
                element = None
            
            return (block, element, modifier)
        
        except Exception:
            return None
    
    def _find_better_block(self, current_block: str, context: FieldContext) -> Optional[str]:
        """Find a better block name based on context and training data."""
        # Look for similar contexts in training data
        if not context.label:
            return None
        
        context_words = set(context.label.lower().split())
        best_block = None
        best_score = 0
        
        for block, examples in self.good_patterns.get('blocks', {}).items():
            if block == current_block:
                continue
            
            # Calculate similarity score
            block_words = set(block.replace('-', ' ').replace('_', ' ').split())
            common_words = context_words & block_words
            
            if common_words:
                score = len(common_words) / len(block_words)
                if score > best_score and score > 0.3:  # Minimum threshold
                    best_score = score
                    best_block = block
        
        return best_block
    
    def _infer_block_from_context(self, context: FieldContext) -> Optional[str]:
        """Infer block name from field context."""
        if not context.label:
            return None
        
        label_lower = context.label.lower()
        
        # Common block patterns from training data
        block_patterns = {
            'owner-information': ['owner', 'applicant', 'insured', 'policyholder'],
            'beneficiary-information': ['beneficiary', 'benefic', 'recipient'],
            'contact-information': ['address', 'phone', 'email', 'contact'],
            'payment': ['payment', 'premium', 'amount', 'billing'],
            'signatures': ['signature', 'sign', 'date'],
            'general-information': ['policy', 'contract', 'number']
        }
        
        for block, keywords in block_patterns.items():
            if any(keyword in label_lower for keyword in keywords):
                return block
        
        return 'general-information'
    
    def _infer_element_from_field(self, field: FormField) -> Optional[str]:
        """Infer element name from field properties."""
        if not field.name:
            return None
        
        name_lower = field.name.lower()
        
        # Common element patterns
        element_patterns = {
            'name': ['name', 'fname', 'lname', 'first', 'last'],
            'address': ['address', 'street'],
            'city': ['city'],
            'state': ['state'],
            'zip': ['zip', 'postal'],
            'phone': ['phone', 'telephone'],
            'email': ['email'],
            'date': ['date', 'dob'],
            'amount': ['amount', 'value'],
            'signature': ['signature']
        }
        
        for element, keywords in element_patterns.items():
            if any(keyword in name_lower for keyword in keywords):
                return element
        
        # Fallback based on field type
        type_mapping = {
            'signature': 'signature',
            'checkbox': 'option',
            'radio': 'option'
        }
        
        return type_mapping.get(field.field_type, 'field')
    
    def _infer_modifier_from_context(self, context: FieldContext) -> Optional[str]:
        """Infer modifier from field context."""
        if not context.label:
            return None
        
        label_lower = context.label.lower()
        
        # Common modifier patterns
        if 'first' in label_lower:
            return 'first'
        elif 'last' in label_lower:
            return 'last'
        elif 'primary' in label_lower:
            return 'primary'
        elif 'secondary' in label_lower:
            return 'secondary'
        
        return None
    
    def _identify_improvements(self, old_name: str, new_name: str) -> List[str]:
        """Identify what improvements were made."""
        improvements = []
        
        if old_name.count('_') != new_name.count('_'):
            improvements.append("fix_structure")
        
        if old_name.lower() != old_name and new_name == new_name.lower():
            improvements.append("fix_casing")
        
        if len(new_name) < len(old_name):
            improvements.append("remove_redundancy")
        
        if 'field-field' in old_name and 'field-field' not in new_name:
            improvements.append("fix_redundant_field")
        
        return improvements
    
    def _names_are_similar(self, name1: str, name2: str) -> bool:
        """Check if two names are structurally similar."""
        # Parse both names
        parts1 = self._parse_bem_name(name1)
        parts2 = self._parse_bem_name(name2)
        
        if not parts1 or not parts2:
            return False
        
        block1, elem1, mod1 = parts1
        block2, elem2, mod2 = parts2
        
        # Check if blocks are similar
        return block1 == block2 or self._blocks_are_similar(block1, block2)
    
    def _blocks_are_similar(self, block1: str, block2: str) -> bool:
        """Check if two blocks are semantically similar."""
        similar_blocks = [
            {'owner-information', 'applicant-information', 'insured-information'},
            {'beneficiary-information', 'recipient-information'},
            {'contact-information', 'address-information'},
            {'payment', 'billing', 'premium'},
        ]
        
        for group in similar_blocks:
            if block1 in group and block2 in group:
                return True
        
        return False