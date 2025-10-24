"""
Post-Dated Check Parser Module
Handles parsing of various PD check date formats from payment comments
"""

import re
from datetime import datetime, date
from typing import Optional, Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)

class PDCheckParser:
    """Parser for extracting post-dated check information from payment comments"""
    
    # Common date patterns found in PD check comments
    DATE_PATTERNS = [
        # Format: POST DATED 02/09/2024
        (r'POST\s+DATED?\s+(\d{1,2})[/-](\d{1,2})[/-](\d{4})', 'mm/dd/yyyy'),
        # Format: PD;- 08/27/2025 or PD:- 08/20/2025
        (r'PD\s*[;:]?\s*-?\s*(\d{1,2})[/-](\d{1,2})[/-](\d{4})', 'mm/dd/yyyy'),
        # Format: PD-8/16/25 SURAFAL
        (r'PD\s*-\s*(\d{1,2})[/-](\d{1,2})[/-](\d{2})(?!\d)', 'mm/dd/yy'),
        # Format: pd:- 08/13/2025
        (r'pd\s*:?\s*-?\s*(\d{1,2})[/-](\d{1,2})[/-](\d{4})', 'mm/dd/yyyy'),
        # Format: Simple date at start or anywhere: 8/17/25 or 08/12/25
        (r'(?:^|\s)(\d{1,2})[/-](\d{1,2})[/-](\d{2})(?!\d)', 'mm/dd/yy'),
        # Format: PD 11 24 22 or PD 11 25 2022
        (r'PD\s+(\d{1,2})\s+(\d{1,2})\s+(\d{2,4})(?!\d)', 'mm dd yy'),
        # Format: PD010623 (MMDDYY) - must be exactly 6 digits
        (r'PD(\d{2})(\d{2})(\d{2})(?!\d)', 'mmddyy'),
        # Format: PD 02172023 (MMDDYYYY) - 8 digits
        (r'PD\s*(\d{2})(\d{2})(\d{4})(?!\d)', 'mmddyyyy'),
        # Format: AZAD PD 010423 or similar
        (r'PD\s*(\d{2})(\d{2})(\d{2})(?!\d)', 'mmddyy'),
        # Format: PD CHK - 02/11/2023 or PD-CHK -02/08/2023
        (r'PD[\s-]+CHK?\s*[-:]?\s*(\d{1,2})[/-](\d{1,2})[/-](\d{4})', 'mm/dd/yyyy'),
        # Format: PD: 07-20-23 or PD:- 07-20-23
        (r'PD\s*:?\s*-?\s*(\d{1,2})[/-](\d{1,2})[/-](\d{2})(?!\d)', 'mm/dd/yy'),
        # Format: PD 3/23/23
        (r'PD\s+(\d{1,2})[/-](\d{1,2})[/-](\d{2})(?!\d)', 'mm/dd/yy'),
        # Format: PD-8/16/25
        (r'PD[-\s]+(\d{1,2})[/-](\d{1,2})[/-](\d{2})(?!\d)', 'mm/dd/yy'),
        # Format: PD 06/08/23
        (r'PD\s+(\d{2})[/-](\d{2})[/-](\d{2})(?!\d)', 'mm/dd/yy'),
        # Format: p d - date format
        (r'p\s*d\s*[-:]?\s*(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})', 'mm/dd/yyyy'),
        # Format: POST DATE with date
        (r'POST\s+DATE[D]?\s+(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})', 'mm/dd/yyyy'),
    ]
    
    @staticmethod
    def parse_date_from_comment(comment: str) -> Optional[date]:
        """
        Extract post-dated check date from payment comment
        
        Args:
            comment: Payment comment string
            
        Returns:
            date object if a PD check date is found, None otherwise
        """
        if not comment:
            return None
            
        comment_upper = comment.upper()
        
        for pattern, format_type in PDCheckParser.DATE_PATTERNS:
            match = re.search(pattern, comment_upper, re.IGNORECASE)
            if match:
                try:
                    groups = match.groups()
                    
                    if format_type == 'mm/dd/yyyy':
                        month, day, year = int(groups[0]), int(groups[1]), int(groups[2])
                    elif format_type == 'mm dd yy':
                        month, day, year = int(groups[0]), int(groups[1]), int(groups[2])
                        # Handle 2 or 4 digit years
                        if year < 100:
                            year = 2000 + year if year < 50 else 1900 + year
                    elif format_type == 'mmddyy':
                        month, day, year = int(groups[0]), int(groups[1]), int(groups[2])
                        year = 2000 + year if year < 50 else 1900 + year
                    elif format_type == 'mmddyyyy':
                        # This is for format like PD 02172023 where groups are ('02', '17', '2023')
                        month = int(groups[0])
                        day = int(groups[1])
                        year = int(groups[2])
                    elif format_type == 'mm/dd/yy':
                        month, day, year = int(groups[0]), int(groups[1]), int(groups[2])
                        year = 2000 + year if year < 50 else 1900 + year
                    else:
                        continue
                    
                    # Validate and create date
                    if 1 <= month <= 12 and 1 <= day <= 31:
                        # Note: The date in the comment is the deposit date
                        return date(year, month, day)
                        
                except (ValueError, IndexError) as e:
                    logger.debug(f"Failed to parse date from pattern {pattern}: {e}")
                    continue
        
        return None
    
    @staticmethod
    def is_pd_check(comment: str) -> bool:
        """
        Check if a payment comment indicates a post-dated check
        
        Args:
            comment: Payment comment string
            
        Returns:
            True if comment indicates a PD check
        """
        if not comment:
            return False
            
        comment_upper = comment.upper()
        
        # Check for common PD check indicators
        pd_indicators = [
            'POST DATED',
            'POST DATE',
            'POSTDATED',
            'PD CHECK',
            'PD CHK',
            'P D -',
            'PD ',
            'PD-',
            'PD:',
            'PD;',
        ]
        
        # Check for PD indicators
        has_pd_indicator = any(indicator in comment_upper for indicator in pd_indicators)
        
        # Also check if it's just a date pattern (like "8/17/25")
        # Only consider it a PD check if it has a date pattern
        import re
        simple_date_pattern = r'^\s*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\s*$'
        is_simple_date = bool(re.match(simple_date_pattern, comment.strip()))
        
        return has_pd_indicator or is_simple_date
    
    @staticmethod
    def extract_pd_info(comment: str) -> Dict[str, any]:
        """
        Extract all post-dated check information from a comment
        
        Args:
            comment: Payment comment string
            
        Returns:
            Dictionary with PD check information
        """
        info = {
            'is_pd_check': False,
            'deposit_date': None,
            'original_comment': comment,
            'parsed_successfully': False
        }
        
        if not comment:
            return info
        
        # Check if it's a PD check
        if PDCheckParser.is_pd_check(comment):
            info['is_pd_check'] = True
            
            # Try to extract the date
            pd_date = PDCheckParser.parse_date_from_comment(comment)
            if pd_date:
                info['deposit_date'] = pd_date
                info['parsed_successfully'] = True
                
                # Calculate days until deposit
                today = date.today()
                days_diff = (pd_date - today).days
                info['days_until_deposit'] = days_diff
                info['is_past_due'] = days_diff < 0
                info['is_due_soon'] = 0 <= days_diff <= 7  # Due within a week
        
        return info
    
    @staticmethod
    def categorize_pd_checks(pd_checks: List[Dict]) -> Dict[str, List]:
        """
        Categorize PD checks by their deposit status
        
        Args:
            pd_checks: List of PD check records
            
        Returns:
            Dictionary with categorized checks
        """
        today = date.today()
        categories = {
            'past_due': [],
            'due_today': [],
            'due_this_week': [],
            'due_this_month': [],
            'future': [],
            'unparseable': []
        }
        
        for check in pd_checks:
            if not check.get('deposit_date'):
                categories['unparseable'].append(check)
                continue
                
            deposit_date = check['deposit_date']
            if isinstance(deposit_date, str):
                deposit_date = datetime.strptime(deposit_date, '%Y-%m-%d').date()
            
            days_diff = (deposit_date - today).days
            
            if days_diff < 0:
                categories['past_due'].append(check)
            elif days_diff == 0:
                categories['due_today'].append(check)
            elif days_diff <= 7:
                categories['due_this_week'].append(check)
            elif days_diff <= 30:
                categories['due_this_month'].append(check)
            else:
                categories['future'].append(check)
        
        return categories
    
    @staticmethod
    def format_for_calendar(pd_checks: List[Dict]) -> List[Dict]:
        """
        Format PD checks for calendar display
        
        Args:
            pd_checks: List of PD check records
            
        Returns:
            List of calendar events
        """
        events = []
        
        for check in pd_checks:
            if check.get('deposit_date'):
                event = {
                    'title': f"${check.get('amount', 0):,.2f} - {check.get('company', 'Unknown')}",
                    'start': check['deposit_date'].isoformat() if isinstance(check['deposit_date'], date) else check['deposit_date'],
                    'amount': check.get('amount', 0),
                    'company': check.get('company', ''),
                    'payment_id': check.get('payment_id', ''),
                    'comment': check.get('comment', ''),
                    'className': 'pd-check-event'
                }
                
                # Add color coding based on amount
                if check.get('amount', 0) >= 10000:
                    event['className'] += ' high-value'
                elif check.get('amount', 0) >= 5000:
                    event['className'] += ' medium-value'
                else:
                    event['className'] += ' low-value'
                    
                # Add status class
                if check.get('is_past_due'):
                    event['className'] += ' past-due'
                elif check.get('is_due_soon'):
                    event['className'] += ' due-soon'
                    
                events.append(event)
        
        return events


# Test function
def test_parser():
    """Test the PD check parser with sample data"""
    test_comments = [
        "POST DATED 02/09/2024",
        "PD 11 24 22",
        "PD010623",
        "PD 02172023",
        "PD CHK - 02/11/2023",
        "PD 3/23/23",
        "PD-8/16/25",
        "RAFIK BHAI - PD CHK - 02/22/2023",
        "CHK - 5126 - PD-CHK -02/08/2023",
        "AZAD PD 010423",
        "Regular payment",
        "PD: 07-20-23",
        "p d - 05/15/2024"
    ]
    
    for comment in test_comments:
        info = PDCheckParser.extract_pd_info(comment)
        if info['is_pd_check']:
            print(f"Comment: {comment}")
            print(f"  Is PD Check: {info['is_pd_check']}")
            print(f"  Deposit Date: {info['deposit_date']}")
            print(f"  Parsed Successfully: {info['parsed_successfully']}")
            if info['deposit_date']:
                print(f"  Days Until Deposit: {info.get('days_until_deposit')}")
            print()


if __name__ == "__main__":
    test_parser()