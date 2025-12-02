"""
GS1 Barcode Parser for Pharmaceutical Products
Handles complex barcode formats with Application Identifiers (AIs)
Example: 'NAVIDOXINE(01) 18906047654987(10) 250203 (17) 012028(21) NVDXN0225'
"""

import re
import logging
from datetime import datetime
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)

class GS1Parser:
    """
    Parser for GS1 barcode format with Application Identifiers (AIs)
    """
    
    # GS1 Application Identifiers mapping
    AI_DEFINITIONS = {
        '01': {'name': 'GTIN', 'description': 'Global Trade Item Number', 'max_length': 14},
        '02': {'name': 'GTIN of Contained Trade Items', 'description': 'Content of a trade item', 'max_length': 14},
        '10': {'name': 'Batch/Lot Number', 'description': 'Batch or lot number', 'max_length': 20},
        '11': {'name': 'Production Date', 'description': 'Production date', 'max_length': 6},
        '13': {'name': 'Packaging Date', 'description': 'Packaging date', 'max_length': 6},
        '15': {'name': 'Best Before Date', 'description': 'Best before date', 'max_length': 6},
        '17': {'name': 'Expiry Date', 'description': 'Expiration date', 'max_length': 6},
        '21': {'name': 'Serial Number', 'description': 'Serial number', 'max_length': 20},
        '37': {'name': 'Count of Items', 'description': 'Number of items contained', 'max_length': 8},
        '310': {'name': 'Net Weight (kg)', 'description': 'Net weight in kilograms', 'max_length': 6},
        '320': {'name': 'Net Weight (lb)', 'description': 'Net weight in pounds', 'max_length': 6},
    }
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset parser state"""
        self.parsed_data = {}
        self.original_barcode = None
        self.product_name = None
        self.is_gs1_format = False
    
    def parse(self, barcode: str) -> Dict:
        """
        Parse GS1 barcode and return structured data
        
        Args:
            barcode: Raw barcode string
            
        Returns:
            Dictionary containing parsed components
        """
        self.reset()
        self.original_barcode = barcode.strip() if barcode else ""
        
        if not self.original_barcode:
            return self._get_result()
        
        # Check if this is GS1 format (contains AI patterns)
        ai_pattern = r'\((\d{2,3})\)'
        if re.search(ai_pattern, self.original_barcode):
            self.is_gs1_format = True
            return self._parse_gs1_format()
        else:
            self.is_gs1_format = False
            return self._parse_simple_format()
    
    def _parse_gs1_format(self) -> Dict:
        """
        Parse GS1 format with Application Identifiers
        
        Example formats:
        - 'NAVIDOXINE(01) 18906047654987(10) 250203 (17) 012028(21) NVDXN0225'
        - '(01)12345678901234(10)BATCH123(17)250101(21)SN12345'
        """
        # Extract product name (text before first AI)
        first_ai_match = re.search(r'\((\d{2,3})\)', self.original_barcode)
        if first_ai_match:
            product_part = self.original_barcode[:first_ai_match.start()].strip()
            if product_part:
                self.product_name = product_part
        
        # Parse all AI patterns
        # Pattern matches: (AI) value (AI) value...
        pattern = r'\((\d{2,3})\)\s*([^\(]*?)(?=\s*\(\d{2,3}\)|$)'
        matches = re.findall(pattern, self.original_barcode)
        
        for ai, value in matches:
            value = value.strip()
            if not value:
                continue
            
            # Store raw value
            self.parsed_data[f'ai_{ai}_raw'] = value
            
            # Process based on AI type
            self._process_ai_value(ai, value)
        
        return self._get_result()
    
    def _process_ai_value(self, ai: str, value: str):
        """Process AI value based on its type"""
        
        if ai == '01':  # GTIN
            # Clean GTIN to be numeric only
            gtin = re.sub(r'\D', '', value)
            if len(gtin) >= 8:  # Minimum valid GTIN length
                self.parsed_data['gtin'] = gtin
        
        elif ai == '10':  # Batch/Lot Number
            self.parsed_data['batch_number'] = value
        
        elif ai == '17':  # Expiry Date
            parsed_date = self._parse_date(value)
            if parsed_date:
                self.parsed_data['expiry_date'] = parsed_date
            else:
                self.parsed_data['expiry_date_raw'] = value
        
        elif ai == '11':  # Production Date
            parsed_date = self._parse_date(value)
            if parsed_date:
                self.parsed_data['production_date'] = parsed_date
            else:
                self.parsed_data['production_date_raw'] = value
        
        elif ai == '15':  # Best Before Date
            parsed_date = self._parse_date(value)
            if parsed_date:
                self.parsed_data['best_before_date'] = parsed_date
            else:
                self.parsed_data['best_before_date_raw'] = value
        
        elif ai == '21':  # Serial Number
            self.parsed_data['serial_number'] = value
        
        elif ai in ['310', '320', '37']:  # Numeric values
            try:
                numeric_value = float(re.sub(r'[^\d.]', '', value))
                self.parsed_data[f'ai_{ai}'] = numeric_value
            except ValueError:
                self.parsed_data[f'ai_{ai}_raw'] = value
        
        else:  # Other AIs
            self.parsed_data[f'ai_{ai}'] = value
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """
        Parse GS1 date format (YYMMDD or DDMMYY) to ISO format
        
        Args:
            date_str: Date in YYMMDD or DDMMYY format
            
        Returns:
            ISO format date string or None if invalid
        """
        if not date_str or len(date_str) < 6:
            logger.warning(f"Date too short or empty: '{date_str}'")
            return None
        
        try:
            # Try YYMMDD format first (standard GS1)
            try:
                yy = int(date_str[:2])
                mm = int(date_str[2:4])
                dd = int(date_str[4:6])
                logger.debug(f"Trying YYMMDD: yy={yy}, mm={mm}, dd={dd}")
                
                # Determine century (assume 2000s for years < 50)
                if yy < 50:
                    yyyy = 2000 + yy
                else:
                    yyyy = 1900 + yy
                
                # Validate date
                if 1 <= mm <= 12 and 1 <= dd <= 31:
                    result = f"{yyyy:04d}-{mm:02d}-{dd:02d}"
                    logger.debug(f"YYMMDD parse successful: {result}")
                    return result
            except Exception as e:
                logger.debug(f"YYMMDD failed: {e}")
                pass
            
            # Try DDMMYY format (common in some regions)
            try:
                dd = int(date_str[:2])
                mm = int(date_str[2:4])
                yy = int(date_str[4:6])
                logger.debug(f"Trying DDMMYY: dd={dd}, mm={mm}, yy={yy}")
                
                # Handle case where month > 12 but could be year (swap them)
                if mm > 12 and yy <= 12:
                    # Swap month and year
                    mm, yy = yy, mm
                    logger.debug(f"Swapped month/year: mm={mm}, yy={yy}")
                
                # Determine century (assume 2000s for years < 50)
                if yy < 50:
                    yyyy = 2000 + yy
                else:
                    yyyy = 1900 + yy
                
                # Validate date
                if 1 <= mm <= 12 and 1 <= dd <= 31:
                    result = f"{yyyy:04d}-{mm:02d}-{dd:02d}"
                    logger.debug(f"DDMMYY parse successful: {result}")
                    return result
            except Exception as e:
                logger.debug(f"DDMMYY failed: {e}")
                pass
            
            # Try YYDDMM format (rare but seen in some systems)
            try:
                yy = int(date_str[:2])
                dd = int(date_str[2:4])
                mm = int(date_str[4:6])
                logger.debug(f"Trying YYDDMM: yy={yy}, dd={dd}, mm={mm}")
                
                # Determine century (assume 2000s for years < 50)
                if yy < 50:
                    yyyy = 2000 + yy
                else:
                    yyyy = 1900 + yy
                
                # Validate date
                if 1 <= mm <= 12 and 1 <= dd <= 31:
                    result = f"{yyyy:04d}-{mm:02d}-{dd:02d}"
                    logger.debug(f"YYDDMM parse successful: {result}")
                    return result
            except Exception as e:
                logger.debug(f"YYDDMM failed: {e}")
                pass
            
            # Smart pharmaceutical date interpretation
            # For formats like 012028, try various pharmaceutical date conventions
            try:
                # Extract components
                p1 = int(date_str[:2])  # First 2 digits
                p2 = int(date_str[2:4])  # Middle 2 digits  
                p3 = int(date_str[4:6])  # Last 2 digits
                
                # Common pharmaceutical date patterns for 6-digit codes:
                # DDMMYY where MM can be interpreted as year if > 12
                # YYDDMM where DD can be month if > 12
                # MMDDYY is most common for pharmaceutical expiry dates
                # Special case: XX20YY might mean month=02, year=20XX
                
                # Test various combinations that make valid dates
                combinations = [
                    (p2, p3, p1),  # MMDDYY (most common for expiry)
                    (p1, p2, p3),  # YYMMDD
                    (p3, p2, p1),  # DDMMYY (swap year and day)
                    (p1, p3, p2),  # YYDDMM
                    (p2, p1, p3),  # MMYYDD (month first, then year)
                ]
                
                # Special case handling for month=20 (should be month=02)
                if p2 == 20:  # Middle is 20, likely month=02
                    combinations.extend([
                        (2, p3, p1),   # Force month=02, keep day and year
                        (p3, 2, p1),   # DD02YY format
                        (2, p1, p3),   # 02YYDD format
                    ])
                
                for i, (candidate_yy, candidate_mm, candidate_dd) in enumerate(combinations):
                    logger.debug(f"Testing combination {i}: yy={candidate_yy}, mm={candidate_mm}, dd={candidate_dd}")
                    
                    # Determine century
                    if candidate_yy < 50:
                        yyyy = 2000 + candidate_yy
                    else:
                        yyyy = 1900 + candidate_yy
                    
                    # Validate date
                    if 1 <= candidate_mm <= 12 and 1 <= candidate_dd <= 31:
                        # Additional check: prefer reasonable pharmaceutical dates
                        # Expiry dates shouldn't be too far in the past or future
                        import datetime
                        try:
                            candidate_date = datetime.date(yyyy, candidate_mm, candidate_dd)
                            today = datetime.date.today()
                            
                            # Reasonable expiry range: last year to 10 years from now
                            if (today - datetime.timedelta(days=365)) <= candidate_date <= (today + datetime.timedelta(days=3650)):
                                result = f"{yyyy:04d}-{candidate_mm:02d}-{candidate_dd:02d}"
                                logger.debug(f"Smart parse successful: {result}")
                                return result
                        except ValueError:
                            continue  # Invalid date (e.g., Feb 30)
                
                logger.debug("No smart combinations yielded valid dates")
                
            except Exception as e:
                logger.debug(f"Smart date parsing failed: {e}")
                pass
            
            logger.warning(f"All date parsing methods failed for '{date_str}'")
            return None
            
        except (ValueError, IndexError) as e:
            # Log error for debugging
            logger.warning(f"Date parsing failed for '{date_str}': {e}")
            return None
    
    def _parse_simple_format(self) -> Dict:
        """Handle simple barcode formats without AIs"""
        # Check if it looks like a pure GTIN
        clean_barcode = re.sub(r'\D', '', self.original_barcode)
        
        if len(clean_barcode) >= 8:  # Minimum GTIN length
            self.parsed_data['gtin'] = clean_barcode
            self.parsed_data['simple_barcode'] = self.original_barcode
        
        return self._get_result()
    
    def _get_result(self) -> Dict:
        """Return the final parsing result"""
        result = {
            'original_barcode': self.original_barcode,
            'product_name': self.product_name,
            'is_gs1_format': self.is_gs1_format,
            'parsed_data': self.parsed_data.copy(),
            'confidence': self._calculate_confidence()
        }
        
        # Extract key components for easier access
        result.update({
            'gtin': self.parsed_data.get('gtin', ''),
            'batch_number': self.parsed_data.get('batch_number', ''),
            'serial_number': self.parsed_data.get('serial_number', ''),
            'expiry_date': self.parsed_data.get('expiry_date', ''),
        })
        
        return result
    
    def _calculate_confidence(self) -> float:
        """
        Calculate parsing confidence score
        
        Returns:
            Float between 0.0 and 1.0
        """
        if not self.original_barcode:
            return 0.0
        
        if self.is_gs1_format:
            # Higher confidence for GS1 format with valid structure
            confidence = 0.7
            
            # Bonus for GTIN presence
            if self.parsed_data.get('gtin'):
                confidence += 0.15
            
            # Bonus for batch number
            if self.parsed_data.get('batch_number'):
                confidence += 0.1
            
            # Bonus for serial number
            if self.parsed_data.get('serial_number'):
                confidence += 0.05
            
            return min(confidence, 1.0)
        else:
            # Lower confidence for simple format
            if self.parsed_data.get('gtin') and len(self.parsed_data['gtin']) >= 8:
                return 0.5
            return 0.3
    
    @staticmethod
    def extract_search_terms(barcode_data: Dict) -> List[str]:
        """
        Extract various search terms from parsed barcode data
        
        Args:
            barcode_data: Parsed barcode data from parse()
            
        Returns:
            List of search terms in priority order
        """
        search_terms = []
        
        # Original barcode (highest priority for exact matches)
        original = barcode_data.get('original_barcode', '').strip()
        if original:
            search_terms.append(original)
        
        # GTIN (for GS1-compatible searches)
        gtin = barcode_data.get('gtin', '').strip()
        if gtin and len(gtin) >= 8:
            search_terms.append(gtin)
        
        # GTIN with check digit variations
        if gtin:
            if len(gtin) == 13:  # EAN-13
                # Try without check digit
                search_terms.append(gtin[:12])
            elif len(gtin) == 14:  # ITF-14
                # Try core 13-digit version
                search_terms.append(gtin[1:])
        
        # Batch + Serial combination
        batch = barcode_data.get('batch_number', '').strip()
        serial = barcode_data.get('serial_number', '').strip()
        if batch and serial:
            search_terms.append(f"{batch}{serial}")
            search_terms.append(f"{batch}-{serial}")
        
        # Individual components
        if batch:
            search_terms.append(batch)
        
        if serial:
            search_terms.append(serial)
        
        # Product name portion
        product_name = barcode_data.get('product_name', '').strip()
        if product_name:
            search_terms.extend(product_name.split())
        
        return search_terms


def parse_barcode(barcode: str) -> Dict:
    """
    Convenience function to parse a barcode
    
    Args:
        barcode: Raw barcode string
        
    Returns:
        Parsed barcode data dictionary
    """
    parser = GS1Parser()
    return parser.parse(barcode)


def is_gs1_barcode(barcode: str) -> bool:
    """
    Check if barcode is in GS1 format
    
    Args:
        barcode: Barcode string to check
        
    Returns:
        True if barcode contains GS1 AI patterns
    """
    if not barcode:
        return False
    ai_pattern = r'\((\d{2,3})\)'
    return bool(re.search(ai_pattern, barcode))


def extract_gtin(barcode: str) -> Optional[str]:
    """
    Extract GTIN from any barcode format
    
    Args:
        barcode: Barcode string
        
    Returns:
        GTIN if found, None otherwise
    """
    if not barcode:
        return None
    
    # Try GS1 parsing first
    if is_gs1_barcode(barcode):
        parsed = parse_barcode(barcode)
        return parsed.get('gtin')
    
    # For simple barcodes, extract numbers
    clean_barcode = re.sub(r'\D', '', barcode)
    if len(clean_barcode) >= 8:
        return clean_barcode
    
    return None


if __name__ == "__main__":
    # Test with the user's example barcode
    test_barcode = 'NAVIDOXINE(01) 18906047654987(10) 250203 (17) 012028(21) NVDXN0225'
    result = parse_barcode(test_barcode)
    
    print("GS1 Barcode Parsing Test:")
    print(f"Original: {result['original_barcode']}")
    print(f"Product Name: {result['product_name']}")
    print(f"Is GS1 Format: {result['is_gs1_format']}")
    print(f"GTIN: {result['gtin']}")
    print(f"Batch Number: {result['batch_number']}")
    print(f"Expiry Date: {result['expiry_date']}")
    print(f"Serial Number: {result['serial_number']}")
    print(f"Confidence: {result['confidence']}")
    print("\nSearch Terms:")
    for i, term in enumerate(GS1Parser.extract_search_terms(result), 1):
        print(f"  {i}. {term}")
