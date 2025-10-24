"""
Enhanced Customer Grouping Module with Fuzzy Name Matching
Uses advanced fuzzy matching on FirstName and LastName fields
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import re
from difflib import SequenceMatcher
import logging
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from database_pymssql import SQLServerConnection

logger = logging.getLogger(__name__)

class EnhancedCustomerGrouper:
    """Enhanced customer grouping with focus on FirstName/LastName fuzzy matching"""
    
    def __init__(self):
        self.name_threshold = 0.75  # 75% similarity for name matching
        self.phone_match_weight = 1.0  # Perfect match if phone numbers match
        self.email_match_weight = 0.9  # High weight for email match
        self.name_match_weight = 0.8   # High weight for name matching
        self.company_match_weight = 0.6
        self.address_match_weight = 0.3
        
        # Common surnames that need extra verification to avoid false positives
        self.common_surnames = {
            'ALI', 'KHAN', 'AHMED', 'SINGH', 'PATEL', 'SHARMA', 'KUMAR', 
            'SMITH', 'JONES', 'WILLIAMS', 'BROWN', 'DAVIS', 'JOHNSON',
            'LEE', 'GARCIA', 'MARTINEZ', 'RODRIGUEZ', 'HERNANDEZ'
        }
        
    def normalize_text(self, text: str) -> str:
        """Normalize text for comparison"""
        if not text:
            return ""
        # Upper case, remove extra spaces
        text = str(text).upper().strip()
        text = re.sub(r'\s+', ' ', text)  # Multiple spaces to single
        # Remove punctuation except spaces
        text = re.sub(r'[^\w\s]', '', text)
        return text.strip()
    
    def normalize_phone(self, phone: str) -> str:
        """Extract digits from phone number"""
        if not phone:
            return ""
        # Keep only digits
        digits = re.sub(r'\D', '', str(phone))
        # Return last 10 digits (US phone number without country code)
        return digits[-10:] if len(digits) >= 10 else digits
    
    def fuzzy_name_match(self, first1: str, last1: str, first2: str, last2: str) -> float:
        """
        Advanced fuzzy matching for names
        Handles variations, nicknames, and swapped first/last names
        """
        first1 = self.normalize_text(first1)
        last1 = self.normalize_text(last1)
        first2 = self.normalize_text(first2)
        last2 = self.normalize_text(last2)
        
        # If no names to compare
        if not (first1 or last1) or not (first2 or last2):
            return 0.0
        
        scores = []
        
        # Exact match
        if first1 == first2 and last1 == last2:
            return 1.0
        
        # Normal order matching
        if first1 and first2:
            first_sim = SequenceMatcher(None, first1, first2).ratio()
            scores.append(first_sim)
        
        if last1 and last2:
            last_sim = SequenceMatcher(None, last1, last2).ratio()
            scores.append(last_sim * 1.2)  # Last name slightly more important
        
        # Check for swapped names
        if first1 and last2:
            swap1 = SequenceMatcher(None, first1, last2).ratio()
            if swap1 > 0.8:
                scores.append(swap1)
        
        if last1 and first2:
            swap2 = SequenceMatcher(None, last1, first2).ratio()
            if swap2 > 0.8:
                scores.append(swap2)
        
        # Check initials
        if first1 and first2:
            if len(first1) == 1 and first2.startswith(first1):
                scores.append(0.7)
            elif len(first2) == 1 and first1.startswith(first2):
                scores.append(0.7)
        
        # Check for common nicknames
        nicknames = {
            'ROBERT': ['BOB', 'BOBBY', 'ROB'],
            'WILLIAM': ['BILL', 'BILLY', 'WILL'],
            'RICHARD': ['RICK', 'RICKY', 'DICK'],
            'MICHAEL': ['MIKE', 'MIKEY'],
            'JAMES': ['JIM', 'JIMMY'],
            'JOHN': ['JOHNNY', 'JACK'],
            'CHRISTOPHER': ['CHRIS'],
            'JOSEPH': ['JOE', 'JOEY'],
            'DANIEL': ['DAN', 'DANNY'],
            'THOMAS': ['TOM', 'TOMMY'],
        }
        
        for full_name, nicks in nicknames.items():
            if first1 == full_name and first2 in nicks:
                scores.append(0.85)
            elif first2 == full_name and first1 in nicks:
                scores.append(0.85)
        
        return max(scores) if scores else 0.0
    
    def calculate_customer_similarity(self, customer1: Dict, customer2: Dict) -> float:
        """Calculate comprehensive similarity between two customers"""
        
        # Check if this is a common surname that needs extra verification
        last1 = self.normalize_text(customer1.get('LastName', ''))
        last2 = self.normalize_text(customer2.get('LastName', ''))
        requires_strong_verification = (last1 in self.common_surnames or last2 in self.common_surnames)
        
        # Phone match - definitive
        phone1 = self.normalize_phone(customer1.get('PhoneNumber', ''))
        phone2 = self.normalize_phone(customer2.get('PhoneNumber', ''))
        phone_matches = phone1 and phone2 and phone1 == phone2
        
        # Email match - also definitive
        email1 = self.normalize_text(customer1.get('EmailAddress', ''))
        email2 = self.normalize_text(customer2.get('EmailAddress', ''))
        email_matches = email1 and email2 and email1 == email2
        
        # If phone or email matches, high confidence regardless of name
        if phone_matches:
            return 0.95  # Very high match on phone
        if email_matches:
            return 0.92  # Very high match on email
        
        # For common surnames, require phone OR email match
        if requires_strong_verification:
            # No phone or email match = not the same person
            return 0.0
        
        scores = []
        weights = []
        
        # Name matching (highest priority)
        name_score = self.fuzzy_name_match(
            customer1.get('FirstName', ''),
            customer1.get('LastName', ''),
            customer2.get('FirstName', ''),
            customer2.get('LastName', '')
        )
        if name_score > 0:
            scores.append(name_score)
            weights.append(self.name_match_weight)
        
        # Company matching
        company1 = self.normalize_text(customer1.get('Company', ''))
        company2 = self.normalize_text(customer2.get('Company', ''))
        if company1 and company2:
            company_sim = SequenceMatcher(None, company1, company2).ratio()
            scores.append(company_sim)
            weights.append(self.company_match_weight)
        
        # Address matching
        address1 = self.normalize_text(customer1.get('Address', ''))
        address2 = self.normalize_text(customer2.get('Address', ''))
        if address1 and address2:
            address_sim = SequenceMatcher(None, address1, address2).ratio()
            scores.append(address_sim)
            weights.append(self.address_match_weight)
        
        # Tax number match
        tax1 = self.normalize_text(customer1.get('TaxNumber', ''))
        tax2 = self.normalize_text(customer2.get('TaxNumber', ''))
        if tax1 and tax2 and tax1 == tax2:
            return 0.90  # High match on tax number
        
        # Calculate weighted average
        if scores and weights:
            total_score = sum(s * w for s, w in zip(scores, weights))
            total_weight = sum(weights)
            return min(total_score / total_weight, 1.0)
        
        return 0.0
    
    def find_customer_groups_soundex(self) -> List[Dict]:
        """Find customer groups using SQL SOUNDEX for phonetic matching with confidence scoring"""
        try:
            with SQLServerConnection() as db:
                # SQL query using SOUNDEX for phonetic matching with stricter verification
                query = """
                WITH ActiveCustomers AS (
                    SELECT *
                    FROM dbo.Customer
                    WHERE LastVisit >= DATEADD(month, -18, GETDATE())
                        OR AccountBalance > 10
                ),
                FuzzyMatchedGroups AS (
                    SELECT DISTINCT
                        c1.FirstName,
                        c1.LastName,
                        c1.ID as PrimaryID,
                        c2.ID as MatchedID,
                        c1.PhoneNumber,
                        c1.EmailAddress,
                        c1.AccountBalance as Balance1,
                        c2.AccountBalance as Balance2,
                        -- Calculate confidence level
                        CASE 
                            WHEN c1.PhoneNumber IS NOT NULL AND c1.PhoneNumber = c2.PhoneNumber THEN 'verified'
                            WHEN c1.EmailAddress IS NOT NULL AND c1.EmailAddress = c2.EmailAddress THEN 'verified'
                            WHEN c1.FirstName = c2.FirstName AND c1.LastName = c2.LastName THEN 'high'
                            ELSE 'potential'
                        END as MatchConfidence
                    FROM ActiveCustomers c1
                    JOIN ActiveCustomers c2
                        ON c1.ID < c2.ID
                        AND SOUNDEX(ISNULL(c1.FirstName, '')) = SOUNDEX(ISNULL(c2.FirstName, ''))
                        AND SOUNDEX(ISNULL(c1.LastName, '')) = SOUNDEX(ISNULL(c2.LastName, ''))
                        AND (
                            -- Require stronger verification for common surnames
                            (c1.LastName NOT IN ('ALI', 'KHAN', 'AHMED', 'SINGH', 'PATEL', 'SHARMA', 'KUMAR', 
                                                 'SMITH', 'JONES', 'WILLIAMS', 'BROWN', 'DAVIS', 'JOHNSON'))
                            OR 
                            (c1.EmailAddress IS NOT NULL AND c1.EmailAddress = c2.EmailAddress)
                            OR 
                            (c1.PhoneNumber IS NOT NULL AND c1.PhoneNumber = c2.PhoneNumber)
                        )
                )
                SELECT 
                    f.FirstName,
                    f.LastName,
                    f.PrimaryID,
                    STUFF((
                        SELECT ',' + CAST(MatchedID as VARCHAR(20))
                        FROM FuzzyMatchedGroups f2
                        WHERE f2.PrimaryID = f.PrimaryID
                            AND f2.FirstName = f.FirstName
                            AND f2.LastName = f.LastName
                        FOR XML PATH(''), TYPE
                    ).value('.', 'VARCHAR(MAX)'), 1, 1, '') as MatchedIDs,
                    COUNT(DISTINCT MatchedID) + 1 as MemberCount,
                    SUM(Balance2) + MAX(Balance1) as TotalBalance,
                    f.PhoneNumber,
                    f.EmailAddress
                FROM FuzzyMatchedGroups f
                GROUP BY 
                    f.FirstName,
                    f.LastName,
                    f.PrimaryID,
                    f.PhoneNumber,
                    f.EmailAddress
                ORDER BY 
                    SUM(Balance2) + MAX(Balance1) DESC
                """
                
                soundex_groups = db.execute_query(query)
                
                if soundex_groups.empty:
                    logger.info("No SOUNDEX groups found")
                    return []
                
                # Process the SOUNDEX results into our standard format
                groups = []
                for _, row in soundex_groups.iterrows():
                    # Get all member IDs
                    member_ids = [int(row['PrimaryID'])]
                    if row['MatchedIDs']:
                        member_ids.extend([int(id.strip()) for id in str(row['MatchedIDs']).split(',')])
                    
                    # Get detailed info for all members
                    placeholders = ','.join(['%s'] * len(member_ids))
                    member_query = f"""
                    SELECT 
                        ID,
                        FirstName,
                        LastName,
                        Company,
                        PhoneNumber,
                        EmailAddress,
                        AccountBalance,
                        CreditLimit,
                        COALESCE(Company, FirstName + ' ' + LastName) as DisplayName
                    FROM dbo.Customer
                    WHERE ID IN ({placeholders})
                    """
                    
                    members_df = db.execute_query(member_query, member_ids)
                    
                    if not members_df.empty:
                        members = []
                        for _, member in members_df.iterrows():
                            members.append({
                                'id': member['ID'],
                                'name': member['DisplayName'],
                                'first_name': member['FirstName'],
                                'last_name': member['LastName'],
                                'company': member['Company'],
                                'phone': member['PhoneNumber'],
                                'email': member['EmailAddress'],
                                'balance': float(member['AccountBalance'] or 0),
                                'credit_limit': float(member['CreditLimit'] or 0)
                            })
                        
                        primary = members[0]
                        total_balance = sum(m['balance'] for m in members)
                        
                        # Determine confidence based on verification strength
                        has_phone_match = False
                        has_email_match = False
                        
                        # Check for shared contact info
                        phones = [m['phone'] for m in members if m['phone']]
                        emails = [m['email'] for m in members if m['email']]
                        
                        if phones:
                            phone_counts = {}
                            for phone in phones:
                                normalized = self.normalize_phone(phone)
                                if normalized:
                                    phone_counts[normalized] = phone_counts.get(normalized, 0) + 1
                            has_phone_match = any(count > 1 for count in phone_counts.values())
                        
                        if emails:
                            email_counts = {}
                            for email in emails:
                                normalized = self.normalize_text(email)
                                if normalized:
                                    email_counts[normalized] = email_counts.get(normalized, 0) + 1
                            has_email_match = any(count > 1 for count in email_counts.values())
                        
                        # Set confidence level
                        if has_phone_match or has_email_match:
                            confidence = 'verified'
                        elif len(members) > 2:
                            confidence = 'high'
                        else:
                            confidence = 'potential'
                        
                        groups.append({
                            'group_id': f"SOUNDEX_{row['PrimaryID']}",
                            'primary_customer': {
                                'id': primary['id'],
                                'name': primary['name'],
                                'first_name': primary['first_name'],
                                'last_name': primary['last_name'],
                                'company': primary['company']
                            },
                            'members': members,
                            'member_count': len(members),
                            'total_balance': total_balance,
                            'confidence': confidence,
                            'match_type': 'SOUNDEX_phonetic',
                            'verification': {
                                'has_phone_match': has_phone_match,
                                'has_email_match': has_email_match
                            }
                        })
                
                logger.info(f"Found {len(groups)} SOUNDEX customer groups")
                return groups
                
        except Exception as e:
            logger.error(f"Error finding SOUNDEX customer groups: {e}")
            return []
    
    def find_customer_groups(self, min_similarity: float = 0.75, use_soundex: bool = False) -> List[Dict]:
        """Find groups of similar customers with enhanced name matching
        
        Args:
            min_similarity: Minimum similarity score for grouping (0-1)
            use_soundex: If True, use SQL SOUNDEX for phonetic matching instead of fuzzy string matching
        """
        if use_soundex:
            return self.find_customer_groups_soundex()
            
        try:
            with SQLServerConnection() as db:
                # Get all customers with complete information
                query = """
                SELECT 
                    ID, 
                    FirstName, 
                    LastName, 
                    Company,
                    Title,
                    PhoneNumber, 
                    EmailAddress,
                    Address, 
                    City, 
                    State, 
                    Zip,
                    AccountBalance,
                    CreditLimit,
                    TaxNumber,
                    TaxExempt,
                    COALESCE(
                        Company,
                        CASE 
                            WHEN FirstName IS NOT NULL OR LastName IS NOT NULL 
                            THEN LTRIM(RTRIM(
                                ISNULL(Title, '') + ' ' + 
                                ISNULL(FirstName, '') + ' ' + 
                                ISNULL(LastName, '')
                            ))
                            ELSE 'Customer #' + CAST(ID as varchar)
                        END
                    ) as DisplayName
                FROM dbo.Customer
                WHERE AccountBalance > 10
                    OR CreditLimit > 100
                ORDER BY AccountBalance DESC
                """
                
                customers = db.execute_query(query)
                
                if customers.empty:
                    logger.info("No customers found for grouping")
                    return []
                
                # Convert to list of dicts for easier processing
                customer_list = customers.to_dict('records')
                
                # Find groups
                groups = []
                processed_ids = set()
                
                for i, customer1 in enumerate(customer_list):
                    if customer1['ID'] in processed_ids:
                        continue
                    
                    group_members = [customer1]
                    processed_ids.add(customer1['ID'])
                    
                    # Find similar customers
                    for j, customer2 in enumerate(customer_list[i+1:], i+1):
                        if customer2['ID'] in processed_ids:
                            continue
                        
                        similarity = self.calculate_customer_similarity(customer1, customer2)
                        
                        if similarity >= min_similarity:
                            group_members.append(customer2)
                            processed_ids.add(customer2['ID'])
                    
                    # Only include groups with multiple members
                    if len(group_members) > 1:
                        total_balance = sum(float(m['AccountBalance'] or 0) for m in group_members)
                        
                        groups.append({
                            'group_id': f"GRP_{customer1['ID']}",
                            'primary_customer': {
                                'id': customer1['ID'],
                                'name': customer1['DisplayName'],
                                'first_name': customer1['FirstName'],
                                'last_name': customer1['LastName'],
                                'company': customer1['Company']
                            },
                            'members': [
                                {
                                    'id': m['ID'],
                                    'name': m['DisplayName'],
                                    'first_name': m['FirstName'],
                                    'last_name': m['LastName'],
                                    'company': m['Company'],
                                    'phone': m['PhoneNumber'],
                                    'email': m['EmailAddress'],
                                    'balance': float(m['AccountBalance'] or 0),
                                    'credit_limit': float(m['CreditLimit'] or 0)
                                }
                                for m in group_members
                            ],
                            'member_count': len(group_members),
                            'total_balance': total_balance,
                            'confidence': 'high' if len(group_members) > 2 else 'medium'
                        })
                
                # Sort by total balance
                groups.sort(key=lambda x: x['total_balance'], reverse=True)
                
                logger.info(f"Found {len(groups)} customer groups")
                return groups
                
        except Exception as e:
            logger.error(f"Error finding customer groups: {e}")
            return []
    
    def compare_matching_methods(self) -> Dict:
        """Compare SOUNDEX and fuzzy matching methods to show differences"""
        try:
            # Get groups using both methods
            soundex_groups = self.find_customer_groups_soundex()
            fuzzy_groups = self.find_customer_groups(min_similarity=0.75, use_soundex=False)
            
            # Create sets of grouped customer IDs for comparison
            soundex_pairs = set()
            for group in soundex_groups:
                ids = [m['id'] for m in group['members']]
                for i in range(len(ids)):
                    for j in range(i+1, len(ids)):
                        soundex_pairs.add(tuple(sorted([ids[i], ids[j]])))
            
            fuzzy_pairs = set()
            for group in fuzzy_groups:
                ids = [m['id'] for m in group['members']]
                for i in range(len(ids)):
                    for j in range(i+1, len(ids)):
                        fuzzy_pairs.add(tuple(sorted([ids[i], ids[j]])))
            
            # Find differences
            only_soundex = soundex_pairs - fuzzy_pairs
            only_fuzzy = fuzzy_pairs - soundex_pairs
            both = soundex_pairs & fuzzy_pairs
            
            return {
                'soundex_groups_count': len(soundex_groups),
                'fuzzy_groups_count': len(fuzzy_groups),
                'soundex_total_pairs': len(soundex_pairs),
                'fuzzy_total_pairs': len(fuzzy_pairs),
                'pairs_in_both': len(both),
                'pairs_only_soundex': len(only_soundex),
                'pairs_only_fuzzy': len(only_fuzzy),
                'soundex_total_balance': sum(g['total_balance'] for g in soundex_groups),
                'fuzzy_total_balance': sum(g['total_balance'] for g in fuzzy_groups),
                'examples': {
                    'soundex_only': list(only_soundex)[:5],  # First 5 examples
                    'fuzzy_only': list(only_fuzzy)[:5]
                }
            }
        except Exception as e:
            logger.error(f"Error comparing matching methods: {e}")
            return {'error': str(e)}
    
    def get_group_detail(self, customer_ids: List[int]) -> Dict:
        """Get detailed information for a group of customers"""
        try:
            if not customer_ids:
                return {}
            
            with SQLServerConnection() as db:
                # Get complete customer details
                placeholders = ','.join(['%s'] * len(customer_ids))
                query = f"""
                SELECT 
                    ID,
                    FirstName,
                    LastName,
                    Company,
                    Title,
                    AccountNumber,
                    PhoneNumber,
                    FaxNumber,
                    EmailAddress,
                    Address,
                    Address2,
                    City,
                    State,
                    Zip,
                    Country,
                    AccountBalance,
                    CreditLimit,
                    TotalSales,
                    TotalVisits,
                    LastVisit,
                    TaxNumber,
                    TaxExempt,
                    Notes,
                    COALESCE(
                        Company,
                        LTRIM(RTRIM(ISNULL(FirstName, '') + ' ' + ISNULL(LastName, '')))
                    ) as DisplayName
                FROM dbo.Customer
                WHERE ID IN ({placeholders})
                """
                
                customers = db.execute_query(query, customer_ids)
                
                if customers.empty:
                    return {}
                
                # Calculate group statistics
                total_balance = customers['AccountBalance'].sum()
                total_credit = customers['CreditLimit'].sum()
                total_sales = customers['TotalSales'].sum()
                total_visits = customers['TotalVisits'].sum()
                
                return {
                    'customers': customers.to_dict('records'),
                    'summary': {
                        'member_count': len(customers),
                        'total_balance': float(total_balance),
                        'total_credit_limit': float(total_credit),
                        'total_lifetime_sales': float(total_sales),
                        'total_visits': int(total_visits),
                        'average_balance': float(total_balance / len(customers)),
                        'has_tax_exempt': any(customers['TaxExempt'])
                    }
                }
                
        except Exception as e:
            logger.error(f"Error getting group detail: {e}")
            return {}