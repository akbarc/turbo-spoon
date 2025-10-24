"""
Customer Grouping Module
Uses fuzzy matching to identify and group related customer entities
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

class CustomerGrouper:
    """Identifies and manages customer groups using fuzzy matching"""
    
    def __init__(self):
        self.similarity_threshold = 0.85  # 85% similarity for auto-suggestion
        self.phone_match_weight = 1.0  # Perfect match if phone numbers match
        self.name_match_weight = 0.7
        self.address_match_weight = 0.3
        
    def normalize_text(self, text: str) -> str:
        """Normalize text for comparison"""
        if not text:
            return ""
        # Upper case, remove extra spaces, remove common suffixes
        text = str(text).upper().strip()
        text = re.sub(r'\s+', ' ', text)  # Multiple spaces to single
        # Remove common business suffixes
        for suffix in ['INC', 'LLC', 'CORP', 'CORPORATION', 'LTD', 'LIMITED', 'COMPANY', 'CO']:
            text = text.replace(f' {suffix}', '').replace(f',{suffix}', '')
        # Remove punctuation
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
    
    def calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings (0-1)"""
        if not str1 or not str2:
            return 0.0
        return SequenceMatcher(None, str1, str2).ratio()
    
    def find_customer_groups(self, min_similarity: float = 0.85) -> List[Dict]:
        """
        Find potential customer groups based on similarity
        
        Returns list of suggested groups with similarity scores
        """
        try:
            with SQLServerConnection() as db:
                # Get all active customers with AR
                query = """
                SELECT 
                    ID,
                    Company,
                    FirstName,
                    LastName,
                    PhoneNumber,
                    Address,
                    AccountBalance,
                    CreditLimit
                FROM dbo.Customer
                WHERE (AccountBalance > 0 OR CreditLimit > 0)
                    AND (FirstName IS NOT NULL OR LastName IS NOT NULL OR Company IS NOT NULL)
                ORDER BY CASE 
                    WHEN FirstName IS NOT NULL AND LastName IS NOT NULL THEN FirstName + ' ' + LastName
                    ELSE Company 
                END
                """
                customers = db.execute_query(query)
                
                if customers.empty:
                    return []
                
                # Find potential groups
                groups = []
                processed_ids = set()
                
                for i, customer1 in customers.iterrows():
                    if customer1['ID'] in processed_ids:
                        continue
                    
                    # Normalize customer1 data - prioritize person name over company
                    person_name1 = f"{customer1['FirstName'] or ''} {customer1['LastName'] or ''}".strip()
                    name1 = self.normalize_text(person_name1 if person_name1 else customer1['Company'])
                    phone1 = self.normalize_phone(customer1['PhoneNumber'])
                    addr1 = self.normalize_text(customer1['Address'])
                    
                    # Find matches for this customer
                    group_members = [{
                        'id': customer1['ID'],
                        'name': customer1['Company'] or f"{customer1['FirstName']} {customer1['LastName']}",
                        'first_name': customer1['FirstName'],
                        'last_name': customer1['LastName'],
                        'phone': customer1['PhoneNumber'],
                        'balance': float(customer1['AccountBalance'] or 0),
                        'credit_limit': float(customer1['CreditLimit'] or 0),
                        'match_score': 1.0  # Perfect match with self
                    }]
                    
                    for j, customer2 in customers.iterrows():
                        if customer2['ID'] == customer1['ID'] or customer2['ID'] in processed_ids:
                            continue
                        
                        # Normalize customer2 data - prioritize person name over company
                        person_name2 = f"{customer2['FirstName'] or ''} {customer2['LastName'] or ''}".strip()
                        name2 = self.normalize_text(person_name2 if person_name2 else customer2['Company'])
                        phone2 = self.normalize_phone(customer2['PhoneNumber'])
                        addr2 = self.normalize_text(customer2['Address'])
                        
                        # Calculate match scores with enhanced fuzzy matching for first/last names
                        first_name_score = 0
                        last_name_score = 0
                        cross_match_score = 0  # For cases where first/last are swapped
                        
                        # Normalize names for comparison
                        fn1 = self.normalize_text(customer1['FirstName'] or '')
                        ln1 = self.normalize_text(customer1['LastName'] or '')
                        fn2 = self.normalize_text(customer2['FirstName'] or '')
                        ln2 = self.normalize_text(customer2['LastName'] or '')
                        
                        if fn1 and fn2:
                            first_name_score = self.calculate_similarity(fn1, fn2)
                            # Check for nicknames/variations (fuzzy match)
                            if first_name_score < 0.9 and len(fn1) > 2 and len(fn2) > 2:
                                # Check if one is substring of other (Bob/Robert, Mike/Michael)
                                if fn1 in fn2 or fn2 in fn1:
                                    first_name_score = max(first_name_score, 0.75)
                                # Check if first 3 letters match (common nickname pattern)
                                elif fn1[:3] == fn2[:3]:
                                    first_name_score = max(first_name_score, 0.7)
                        
                        if ln1 and ln2:
                            last_name_score = self.calculate_similarity(ln1, ln2)
                            # Boost score for exact last name match (most important for family grouping)
                            if ln1 == ln2:
                                last_name_score = 1.0
                        
                        # Check for swapped first/last names
                        if fn1 and ln2:
                            cross_match1 = self.calculate_similarity(fn1, ln2)
                        else:
                            cross_match1 = 0
                        if ln1 and fn2:
                            cross_match2 = self.calculate_similarity(ln1, fn2)
                        else:
                            cross_match2 = 0
                        cross_match_score = (cross_match1 + cross_match2) / 2 if (cross_match1 > 0.8 or cross_match2 > 0.8) else 0
                        
                        # Combined name score with better weighting
                        if last_name_score >= 0.9 and first_name_score >= 0.6:
                            # Strong match: same last name, similar first name
                            name_score = 0.95
                        elif last_name_score >= 0.9:
                            # Same last name, different first name (family members)
                            name_score = 0.85
                        elif first_name_score >= 0.9 and last_name_score >= 0.7:
                            # Same first name, similar last name
                            name_score = 0.8
                        elif cross_match_score > 0.8:
                            # Names are swapped
                            name_score = 0.9
                        elif first_name_score > 0 and last_name_score > 0:
                            # Both names have some similarity
                            name_score = (first_name_score * 0.4 + last_name_score * 0.6)
                        else:
                            # Fallback to full name comparison
                            name_score = self.calculate_similarity(name1, name2)
                        
                        phone_match = 1.0 if (phone1 and phone2 and phone1 == phone2) else 0.0
                        addr_score = self.calculate_similarity(addr1, addr2) if (addr1 and addr2) else 0.0
                        
                        # Weighted total score with higher priority for name matching
                        total_score = (
                            name_score * 0.8 +  # Increased weight for name matching
                            phone_match * 1.0 +
                            addr_score * 0.2    # Reduced weight for address
                        ) / 2.0
                        
                        # Check if this is a match
                        if total_score >= min_similarity or phone_match == 1.0:
                            group_members.append({
                                'id': customer2['ID'],
                                'name': customer2['Company'] or f"{customer2['FirstName']} {customer2['LastName']}",
                                'first_name': customer2['FirstName'],
                                'last_name': customer2['LastName'],
                                'phone': customer2['PhoneNumber'],
                                'balance': float(customer2['AccountBalance'] or 0),
                                'credit_limit': float(customer2['CreditLimit'] or 0),
                                'match_score': total_score,
                                'match_reasons': {
                                    'name_similarity': name_score,
                                    'phone_match': phone_match == 1.0,
                                    'address_similarity': addr_score
                                }
                            })
                            processed_ids.add(customer2['ID'])
                    
                    # If we found a group (more than 1 member)
                    if len(group_members) > 1:
                        processed_ids.add(customer1['ID'])
                        
                        # Calculate group stats
                        total_balance = sum(m['balance'] for m in group_members)
                        total_credit = sum(m['credit_limit'] for m in group_members)
                        
                        # Create a better group name by finding common elements
                        # Collect all first and last names
                        first_names = [m['first_name'] for m in group_members if m.get('first_name')]
                        last_names = [m['last_name'] for m in group_members if m.get('last_name')]
                        companies = [m['name'] for m in group_members if m.get('name') and not (m.get('first_name') or m.get('last_name'))]
                        
                        # Find most common last name (likely family name)
                        common_last_name = None
                        if last_names:
                            from collections import Counter
                            last_name_counts = Counter(last_names)
                            most_common = last_name_counts.most_common(1)
                            if most_common and most_common[0][1] > 1:
                                common_last_name = most_common[0][0]
                        
                        # Build group name
                        if common_last_name:
                            # Family group - use common last name
                            unique_first_names = list(set(first_names))[:3]
                            if unique_first_names:
                                group_name = f"{common_last_name} Family ({', '.join(unique_first_names)})"
                            else:
                                group_name = f"{common_last_name} Group"
                        elif len(set(last_names)) == 1 and last_names:
                            # All same last name
                            group_name = f"{last_names[0]} Group"
                        elif companies:
                            # Company-based group
                            group_name = companies[0]
                            if len(companies) > 1:
                                group_name += f" (+{len(companies)-1} related)"
                        else:
                            # Use individual names
                            unique_names = set()
                            for member in group_members[:3]:
                                if member.get('first_name') and member.get('last_name'):
                                    unique_names.add(f"{member['first_name']} {member['last_name']}")
                            group_name = ', '.join(list(unique_names)[:2]) if unique_names else "Related Customers"
                        
                        groups.append({
                            'suggested_name': group_name,
                            'members': group_members,
                            'member_count': len(group_members),
                            'total_ar_balance': total_balance,
                            'total_credit_limit': total_credit,
                            'avg_match_score': sum(m['match_score'] for m in group_members) / len(group_members)
                        })
                
                # Sort by total AR balance
                groups.sort(key=lambda x: x['total_ar_balance'], reverse=True)
                
                return groups
                
        except Exception as e:
            logger.error(f"Error finding customer groups: {e}")
            return []
    
    def get_saved_groups(self) -> List[Dict]:
        """
        Get previously saved customer groups
        Note: This would normally read from a database table
        For now, using a simple query to identify obvious groups
        """
        try:
            with SQLServerConnection() as db:
                # Get customers that likely belong to groups based on naming patterns
                query = """
                WITH CustomerGroups AS (
                    SELECT 
                        CASE 
                            -- Define known group patterns here
                            WHEN Company LIKE '%KHERANI%' OR Company LIKE '%MALIK%' THEN 'KHERANI_GROUP'
                            WHEN Company LIKE '%PATEL%' THEN 'PATEL_GROUP'
                            WHEN Company LIKE '%SHAH%' THEN 'SHAH_GROUP'
                            WHEN Company LIKE '%SINGH%' THEN 'SINGH_GROUP'
                            -- Add more patterns as needed
                            ELSE NULL
                        END as GroupName,
                        ID,
                        COALESCE(Company, FirstName + ' ' + LastName) as CustomerName,
                        AccountBalance,
                        CreditLimit,
                        PhoneNumber
                    FROM dbo.Customer
                    WHERE AccountBalance > 0 OR CreditLimit > 0
                )
                SELECT 
                    GroupName,
                    COUNT(*) as MemberCount,
                    SUM(AccountBalance) as TotalBalance,
                    SUM(CreditLimit) as TotalCreditLimit
                FROM CustomerGroups
                WHERE GroupName IS NOT NULL
                GROUP BY GroupName
                HAVING COUNT(*) > 1
                ORDER BY SUM(AccountBalance) DESC
                """
                
                result = db.execute_query(query)
                
                if result.empty:
                    return []
                
                groups = []
                for _, row in result.iterrows():
                    # Get member details separately
                    group_name = row['GroupName']
                    member_query = """
                    SELECT 
                        ID,
                        COALESCE(Company, FirstName + ' ' + LastName) as CustomerName
                    FROM dbo.Customer
                    WHERE CASE 
                        WHEN Company LIKE '%KHERANI%' OR Company LIKE '%MALIK%' THEN 'KHERANI_GROUP'
                        WHEN Company LIKE '%PATEL%' THEN 'PATEL_GROUP'
                        WHEN Company LIKE '%SHAH%' THEN 'SHAH_GROUP'
                        WHEN Company LIKE '%SINGH%' THEN 'SINGH_GROUP'
                        ELSE NULL
                    END = %s
                    """
                    members_df = db.execute_query(member_query, [group_name])
                    
                    groups.append({
                        'group_name': row['GroupName'],
                        'member_count': int(row['MemberCount']),
                        'total_balance': float(row['TotalBalance'] or 0),
                        'total_credit_limit': float(row['TotalCreditLimit'] or 0),
                        'members': members_df['CustomerName'].tolist() if not members_df.empty else [],
                        'member_ids': members_df['ID'].tolist() if not members_df.empty else []
                    })
                
                return groups
                
        except Exception as e:
            logger.error(f"Error getting saved groups: {e}")
            return []
    
    def create_group(self, group_name: str, customer_ids: List[int]) -> bool:
        """
        Create a new customer group
        Note: In production, this would save to a CustomerGroups table
        """
        try:
            # In a real implementation, we would:
            # 1. Create a CustomerGroups table
            # 2. Insert the group
            # 3. Link customers to the group
            
            logger.info(f"Creating group '{group_name}' with customers: {customer_ids}")
            # For now, just log it
            return True
            
        except Exception as e:
            logger.error(f"Error creating group: {e}")
            return False
    
    def get_group_detail(self, customer_ids: List[int]) -> Dict:
        """Get detailed information for a group of customers"""
        try:
            with SQLServerConnection() as db:
                if not customer_ids:
                    return {}
                
                # Build ID list for SQL
                id_list = ','.join(str(id) for id in customer_ids)
                
                # Get combined metrics
                query = f"""
                WITH GroupMetrics AS (
                    SELECT 
                        COUNT(DISTINCT c.ID) as customer_count,
                        SUM(c.AccountBalance) as total_ar,
                        SUM(c.CreditLimit) as total_credit_limit,
                        AVG(c.AccountBalance) as avg_ar,
                        MAX(c.AccountBalance) as max_ar,
                        MIN(c.LastVisit) as earliest_visit,
                        MAX(c.LastVisit) as latest_visit,
                        SUM(c.TotalSales) as lifetime_sales
                    FROM dbo.Customer c
                    WHERE c.ID IN ({id_list})
                ),
                PaymentMetrics AS (
                    SELECT 
                        COUNT(*) as payment_count,
                        SUM(Amount) as total_payments,
                        AVG(Amount) as avg_payment,
                        MAX(Time) as last_payment_date
                    FROM dbo.Payment
                    WHERE CustomerID IN ({id_list})
                        AND Time >= DATEADD(month, -12, GETDATE())
                ),
                InvoiceMetrics AS (
                    SELECT 
                        COUNT(*) as open_invoice_count,
                        MIN(Date) as oldest_invoice,
                        MAX(Date) as newest_invoice,
                        SUM(CASE WHEN DATEDIFF(day, Date, GETDATE()) > 90 THEN Balance ELSE 0 END) as over_90_balance
                    FROM dbo.AccountReceivable
                    WHERE CustomerID IN ({id_list})
                        AND Balance > 0
                )
                SELECT 
                    gm.*,
                    pm.payment_count,
                    pm.total_payments,
                    pm.avg_payment,
                    pm.last_payment_date,
                    im.open_invoice_count,
                    im.oldest_invoice,
                    im.newest_invoice,
                    im.over_90_balance
                FROM GroupMetrics gm
                CROSS JOIN PaymentMetrics pm
                CROSS JOIN InvoiceMetrics im
                """
                
                metrics_df = db.execute_query(query)
                metrics = metrics_df.to_dict('records') if not metrics_df.empty else []
                
                # Get member details
                members_query = f"""
                SELECT 
                    ID,
                    COALESCE(Company, FirstName + ' ' + LastName) as CustomerName,
                    PhoneNumber,
                    AccountBalance,
                    CreditLimit,
                    LastVisit,
                    (SELECT MAX(Time) FROM dbo.Payment WHERE CustomerID = c.ID) as LastPayment
                FROM dbo.Customer c
                WHERE ID IN ({id_list})
                ORDER BY AccountBalance DESC
                """
                
                members = db.execute_query(members_query)
                
                return {
                    'metrics': metrics[0] if metrics else {},
                    'members': members.to_dict('records') if not members.empty else []
                }
                
        except Exception as e:
            logger.error(f"Error getting group detail: {e}")
            return {}
    
    def analyze_group_patterns(self, customer_ids: List[int]) -> Dict:
        """Analyze payment patterns for a group of customers"""
        try:
            with SQLServerConnection() as db:
                if not customer_ids:
                    return {}
                
                id_list = ','.join(str(id) for id in customer_ids)
                
                # Analyze payment patterns
                query = f"""
                WITH PaymentPatterns AS (
                    SELECT 
                        p.CustomerID,
                        DATEPART(dw, p.Time) as DayOfWeek,
                        DATEPART(day, p.Time) as DayOfMonth,
                        p.Amount,
                        DATEDIFF(day, 
                            (SELECT TOP 1 Time FROM [dbo].[Transaction] t 
                             WHERE t.CustomerID = p.CustomerID 
                             AND t.Time < p.Time 
                             ORDER BY Time DESC), 
                            p.Time) as DaysToPay
                    FROM dbo.Payment p
                    WHERE p.CustomerID IN ({id_list})
                        AND p.Time >= DATEADD(month, -6, GETDATE())
                )
                SELECT 
                    -- Most common payment day of week
                    (SELECT TOP 1 DayOfWeek FROM PaymentPatterns 
                     GROUP BY DayOfWeek 
                     ORDER BY COUNT(*) DESC) as most_common_day_of_week,
                    
                    -- Average days to pay
                    AVG(DaysToPay) as avg_days_to_pay,
                    
                    -- Payment consistency (standard deviation)
                    STDEV(DaysToPay) as payment_consistency,
                    
                    -- Preferred payment range (day of month)
                    AVG(CASE WHEN DayOfMonth <= 10 THEN 1 ELSE 0 END) * 100 as pct_early_month,
                    AVG(CASE WHEN DayOfMonth BETWEEN 11 AND 20 THEN 1 ELSE 0 END) * 100 as pct_mid_month,
                    AVG(CASE WHEN DayOfMonth > 20 THEN 1 ELSE 0 END) * 100 as pct_late_month,
                    
                    -- Payment amounts
                    AVG(Amount) as avg_payment_amount,
                    MIN(Amount) as min_payment,
                    MAX(Amount) as max_payment,
                    
                    COUNT(*) as total_payments
                FROM PaymentPatterns
                """
                
                patterns_df = db.execute_query(query)
                patterns = patterns_df.to_dict('records') if not patterns_df.empty else []
                
                return patterns[0] if patterns else {}
                
        except Exception as e:
            logger.error(f"Error analyzing group patterns: {e}")
            return {}