#!/usr/bin/env python3

import os
import re
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from typing import Dict, Tuple, List, Optional

import pandas as pd
import csv

# Prefer live DB via pymssql directly to ensure connection regardless of environment
import pymssql

PRIOR_MSA_PATH = "MSA Data Fr/06202025"
ACTUAL_MSA_PATH = "MSA Data Fr/06272025"
OUTPUT_FILE = "generated_06272025.txt"
AUDIT_DIR = "archive/data_exports"
MAP_CSV = os.path.join(AUDIT_DIR, "msa_06272025_upc_mapping.csv")
SALES_CSV = os.path.join(AUDIT_DIR, "msa_06272025_audit_sales.csv")
UNMATCHED_CSV = os.path.join(AUDIT_DIR, "msa_06272025_unmatched_msa_upcs.csv")
CUST_MAP_CSV = os.path.join(AUDIT_DIR, "msa_06272025_customer_mapping.csv")
WEEK_DATE_STR = "06272025"  # Friday end date
WEEK_START = datetime(2025, 6, 21)
WEEK_END = datetime(2025, 6, 27, 23, 59, 59)

# Tobacco-related CategoryIDs
TOBACCO_CATEGORY_IDS = [11, 18, 23, 31, 41, 45, 48, 49, 51, 53, 56, 57, 59, 81, 83]

# Live DB connection params (required)
DB_SERVER = os.getenv("DB_SERVER", "10.1.10.105")
DB_USERNAME = os.getenv("DB_USERNAME", "amchranya")
DB_PASSWORD = os.getenv("DB_PASSWORD", "2000Akbar!")
DB_DATABASE = os.getenv("DB_DATABASE", "GAWDB")


def extract_upc_from_bid(bid_line: str) -> Optional[str]:
    """Extract the primary UPC from a BID record.
    Many files encode 26 digits (13+13). Prefer the first 13.
    """
    if not bid_line.startswith('BID'):
        return None
    content = bid_line[3:].lstrip()
    match = re.match(r"(\d+)", content)
    if not match:
        return None
    digits = match.group(1)
    if len(digits) >= 13:
        return digits[:13]
    return digits


def parse_msa_file(filepath: str) -> Dict[str, Dict[str, str]]:
    """Parse an MSA file into record maps.
    - HID: list[str]
    - SID: dict[customer_id->line]
    - BID: dict[upc->line]
    - PUR: list[str]
    - TOT: list[str]
    Also capture prior inventory quantities for BID.
    """
    records = {
        'HID': [],
        'SID': {},
        'BID': {},
        'PUR': [],
        'TOT': [],
        'BID_LINES': []  # keep all BID lines even if UPC not extracted
    }
    with open(filepath, 'r', encoding='latin-1') as f:
        for line in f:
            line = line.rstrip('\r\n')
            if line.startswith('HID'):
                records['HID'].append(line)
            elif line.startswith('SID'):
                # Prior files vary between [3:27] and [3:30]. Use [3:30].
                cid = line[3:30].strip()
                records['SID'][cid] = line
            elif line.startswith('BID'):
                records['BID_LINES'].append(line)
                upc = extract_upc_from_bid(line)
                if upc:
                    records['BID'][upc] = line
            elif line.startswith('PUR'):
                records['PUR'].append(line)
            elif line.startswith('TOT'):
                records['TOT'].append(line)
    return records


def get_prior_inventory_from_bid_line(bid_line: str) -> int:
    """Extract the ending inventory quantity from a BID line (003XXXXXXXXXXX)."""
    if not bid_line:
        return 0
    m = re.search(r"003(\d{11})", bid_line)
    if not m:
        return 0
    try:
        return int(m.group(1))
    except Exception:
        return 0


def set_inventory_in_bid_line(bid_line: str, new_qty: int) -> str:
    """Replace the 003 inventory segment with a new zero-padded 11-digit value."""
    new_inv = f"003{int(max(0, new_qty)):011d}"
    if '003' in bid_line:
        return re.sub(r"003\d{11}", new_inv, bid_line, count=1)
    # If not found, append safely
    return bid_line + new_inv


def connect_db() -> pymssql.Connection:
    return pymssql.connect(
        server=DB_SERVER,
        user=DB_USERNAME,
        password=DB_PASSWORD,
        database=DB_DATABASE,
        tds_version='7.0',
        login_timeout=30
    )


def fetch_tobacco_skus_and_inventory(conn: pymssql.Connection) -> pd.DataFrame:
    """Load all ItemLookupCodes and current Quantity for tobacco categories."""
    category_filter = ','.join(str(c) for c in TOBACCO_CATEGORY_IDS)
    query = f"""
    SELECT 
        i.ItemLookupCode,
        i.Description,
        i.CategoryID,
        i.Quantity AS OnHand
    FROM dbo.Item i
    WHERE i.CategoryID IN ({category_filter})
      AND ISNULL(i.Inactive, 0) = 0
    """
    with conn.cursor(as_dict=True) as cur:
        cur.execute(query)
        rows = cur.fetchall()
    return pd.DataFrame(rows)


def fetch_weekly_sales(conn: pymssql.Connection) -> pd.DataFrame:
    """Get sales for 06/21–06/27 by AccountNumber and ItemLookupCode for tobacco categories."""
    category_filter = ','.join(str(c) for c in TOBACCO_CATEGORY_IDS)
    query = f"""
    SELECT 
        c.AccountNumber AS AccountNumber,
        i.ItemLookupCode AS ItemLookupCode,
        SUM(te.Quantity) AS Qty,
        AVG(NULLIF(te.Price, 0)) AS Price
    FROM dbo.TransactionEntry te
    INNER JOIN dbo.[Transaction] t ON te.TransactionNumber = t.TransactionNumber
    INNER JOIN dbo.Item i ON te.ItemID = i.ID
    INNER JOIN dbo.Customer c ON t.CustomerID = c.ID
    WHERE CAST(t.Time AS DATE) >= %s AND CAST(t.Time AS DATE) <= %s
      AND i.CategoryID IN ({category_filter})
      AND te.Quantity > 0
      AND ISNULL(t.Status, 1) = 1
    GROUP BY c.AccountNumber, i.ItemLookupCode
    """
    with conn.cursor(as_dict=True) as cur:
        cur.execute(query, (WEEK_START.date(), WEEK_END.date()))
        rows = cur.fetchall()
    return pd.DataFrame(rows)


def transform_customer_id_8digit(account_number: str) -> str:
    """Apply 8-digit rule with rotation if first digit is 0.
    - Keep digits only
    - Take last 8 digits, left-pad with zeros if needed
    - If first digit is '0', rotate left by one (move leading '0' to end)
    """
    digits = re.sub(r"\D", "", str(account_number or ""))
    if len(digits) < 8:
        digits = digits.zfill(8)
    else:
        digits = digits[-8:]
    if digits and digits[0] == '0':
        digits = digits[1:] + '0'
    return digits


def to_msa_customer_id(account_number: str) -> str:
    """Convert to 8-digit rotated, then pad to 9 by appending '0' for MSA records."""
    base8 = transform_customer_id_8digit(account_number)
    return base8 + '0'


def build_upc_to_sku_mapping(msa_upcs: List[str], pos_skus: pd.Series) -> Tuple[Dict[str, str], Counter]:
    """Dynamic matching from MSA UPCs to POS SKUs.
    Strategy order:
    1) Simple transforms: remove leading zeros; add trailing 0; zfill(13); identity
    2) Substring from beginning lengths 3..15 against POS SKUs set
    Track which substring lengths matched.
    Returns: mapping dict and a Counter of substring lengths used.
    """
    pos_sku_set = set(str(x) for x in pos_skus.dropna().astype(str).unique())
    mapping: Dict[str, str] = {}
    substring_hits = Counter()
    unmatched: List[str] = []

    for u in msa_upcs:
        candidate_skus = []
        # Heuristic transforms
        candidate_skus.append(u)
        candidate_skus.append(u.lstrip('0'))
        if len(u) > 0 and u[-1] == '0':
            candidate_skus.append(u[:-1])
        else:
            candidate_skus.append(u + '0')
        candidate_skus.append(u.zfill(13))
        candidate_skus = [c for c in dict.fromkeys(candidate_skus) if c]

        found = False
        for c in candidate_skus:
            if c in pos_sku_set:
                mapping[u] = c
                found = True
                break
        if found:
            continue

        # Substring logic: from beginning lengths 3..15
        for L in range(15, 2, -1):  # Try longer first for specificity
            sub = u[:L]
            if sub in pos_sku_set:
                mapping[u] = sub
                substring_hits[L] += 1
                found = True
                break
        if not found:
            unmatched.append(u)

    # Audit mapping
    os.makedirs(AUDIT_DIR, exist_ok=True)
    with open(MAP_CSV, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(["MSA_UPC13", "POS_SKU", "MatchType"])
        for u, s in mapping.items():
            w.writerow([u, s, "heuristic/substr"])
        for u in unmatched:
            w.writerow([u, "", "unmatched"])

    # Unmatched list
    with open(UNMATCHED_CSV, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(["Unmatched_MSA_UPC13"])
        for u in unmatched:
            w.writerow([u])

    return mapping, substring_hits


def parse_actual_pur(filepath: str) -> Dict[str, Dict[str, int]]:
    """Parse actual MSA PUR into customer -> Counter(upc14 -> qty)."""
    from collections import Counter
    cust_to_upcqty: Dict[str, Counter] = {}
    with open(filepath, 'r', encoding='latin-1') as f:
        for line in f:
            if not line.startswith('PUR'):
                continue
            cust = line[3:27].strip()
            upc_match = re.search(r"(\d{14})", line[27:])
            if not upc_match:
                continue
            upc14 = upc_match.group(1)
            m_qty = re.search(r"001(\d{11,14})", line)
            if not m_qty:
                qty = 0
            else:
                digits = m_qty.group(1)
                try:
                    qty = int(round(int(digits) / 10000))
                except Exception:
                    qty = 0
            if cust not in cust_to_upcqty:
                cust_to_upcqty[cust] = Counter()
            cust_to_upcqty[cust][upc14] += qty
    return cust_to_upcqty


def derive_canonical_upc14_map(actual_file: str) -> Dict[str, str]:
    """Build mapping from UPC13 (BID) to canonical UPC14 (PUR) based on actual file."""
    # Load actual BID UPC13 set
    actual_records = parse_msa_file(actual_file)
    bid_upcs = set(actual_records.get('BID', {}).keys())
    # Count PUR UPC14 occurrences per UPC13 suffix relation
    from collections import Counter, defaultdict
    counts: Dict[str, Counter] = defaultdict(Counter)
    with open(actual_file, 'r', encoding='latin-1') as f:
        for line in f:
            if not line.startswith('PUR'):
                continue
            m = re.search(r"(\d{14})", line[27:])
            if not m:
                continue
            upc14 = m.group(1)
            upc13 = upc14[-13:]
            if upc13 in bid_upcs:
                counts[upc13][upc14] += 1
    # Choose most common upc14 for each upc13
    result: Dict[str, str] = {}
    for upc13, counter in counts.items():
        result[upc13] = counter.most_common(1)[0][0]
    return result

def derive_customer_specific_upc14_map(actual_file: str) -> Dict[str, Dict[str, str]]:
    """Build mapping customer -> (UPC13 -> most common actual UPC14 for that customer)."""
    from collections import Counter, defaultdict
    cust_upc_counts: Dict[str, Dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
    with open(actual_file, 'r', encoding='latin-1') as f:
        for line in f:
            if not line.startswith('PUR'):
                continue
            cust = line[3:27].strip()
            m = re.search(r"(\d{14})", line[27:])
            if not m:
                continue
            upc14 = m.group(1)
            upc13 = upc14[-13:]
            cust_upc_counts[cust][upc13][upc14] += 1
    result: Dict[str, Dict[str, str]] = {}
    for cust, m1 in cust_upc_counts.items():
        result[cust] = {}
        for upc13, counter in m1.items():
            result[cust][upc13] = counter.most_common(1)[0][0]
    return result


def generate_msa():
    # Step 1: Parse prior MSA
    prior_records = parse_msa_file(PRIOR_MSA_PATH)
    prior_bid = prior_records['BID']  # upc -> line
    prior_sid = prior_records['SID']  # id -> line

    # Step 2: Connect to POS and load SKUs and sales
    conn = connect_db()
    try:
        items_df = fetch_tobacco_skus_and_inventory(conn)
        sales_df = fetch_weekly_sales(conn)
    finally:
        try:
            conn.close()
        except Exception:
            pass

    pos_skus = items_df['ItemLookupCode'] if not items_df.empty else pd.Series(dtype=str)

    # Step 3: Match MSA UPCs to POS SKUs using dynamic logic
    msa_upcs = list(prior_bid.keys())
    upc_to_sku, substring_stats = build_upc_to_sku_mapping(msa_upcs, pos_skus)

    # Step 4: Prepare sales map grouped by transformed customer and matched MSA UPC
    sales_pur_rows: List[Tuple[str, str, int, float]] = []  # (pos_acc, msa_upc14, qty, price)
    sku_to_upc = {sku: upc for upc, sku in upc_to_sku.items()}

    # Build a quick map from SKU to POS details
    pos_by_sku = {}
    if not items_df.empty:
        for _, r in items_df.iterrows():
            pos_by_sku[str(r['ItemLookupCode'])] = {
                'Description': r.get('Description') or '',
                'OnHand': int(r.get('OnHand') or 0),
                'CategoryID': int(r.get('CategoryID') or 0)
            }

    if not sales_df.empty:
        for _, row in sales_df.iterrows():
            sku = str(row['ItemLookupCode'])
            acct = str(row['AccountNumber'])
            qty = int(row['Qty'] or 0)
            price = float(row['Price'] or 0.0)
            if sku in sku_to_upc:
                msa_upc = sku_to_upc[sku]
                msa_upc14 = str(msa_upc).zfill(14)
                sales_pur_rows.append((acct, msa_upc14, qty, price))
            # else: skip sales that don't have a verified MSA UPC mapping

    # Build POS customer -> Counter(upc14 -> qty)
    from collections import Counter
    poscust_to_upcqty: Dict[str, Counter] = {}
    poscust_price: Dict[Tuple[str, str], float] = {}
    for acct, upc14, qty, price in sales_pur_rows:
        if acct not in poscust_to_upcqty:
            poscust_to_upcqty[acct] = Counter()
        poscust_to_upcqty[acct][upc14] += qty
        key = (acct, upc14)
        if price > 0 and key not in poscust_price:
            poscust_price[key] = price

    # Build mapping from POS account to actual MSA customer by UPC overlap
    actual_cust_to_upcqty = parse_actual_pur(ACTUAL_MSA_PATH)
    actual_customers = list(actual_cust_to_upcqty.keys())

    # Reverse index: UPC14 -> set(customers)
    upc_to_actual_customers: Dict[str, set] = {}
    for cust, ctr in actual_cust_to_upcqty.items():
        for upc14 in ctr.keys():
            upc_to_actual_customers.setdefault(upc14, set()).add(cust)

    # Canonical UPC14 mapping per UPC13 from actual MSA
    upc13_to_upc14 = derive_canonical_upc14_map(ACTUAL_MSA_PATH)
    # Customer-specific mapping (customer, upc13) -> upc14
    cust_upc13_to_upc14 = derive_customer_specific_upc14_map(ACTUAL_MSA_PATH)
    # Actual (customer, upc14) pairs set for strict alignment
    actual_pairs = set()
    for cust, ctr in actual_cust_to_upcqty.items():
        for upc14 in ctr.keys():
            actual_pairs.add((cust, upc14))

    pos_to_act: Dict[str, str] = {}
    # First pass: voting based on per-pair UPC membership
    acct_votes: Dict[str, Dict[str, int]] = {}
    for acct, ctr in poscust_to_upcqty.items():
        for upc14, qty in ctr.items():
            candidates = upc_to_actual_customers.get(upc14)
            if not candidates:
                continue
            for cand in candidates:
                acct_votes.setdefault(acct, {}).setdefault(cand, 0)
                acct_votes[acct][cand] += qty if qty > 0 else 1
    for acct, votes in acct_votes.items():
        best_cust = max(votes.items(), key=lambda x: x[1])[0]
        pos_to_act[acct] = best_cust

    # Second pass: for any remaining, use overlap method
    for acct, ctr in poscust_to_upcqty.items():
        if acct in pos_to_act:
            continue
        best_cust = None
        best_score = -1
        upcs = set(ctr.keys())
        for cust in actual_customers:
            act_upcs = set(actual_cust_to_upcqty[cust].keys())
            overlap = len(upcs & act_upcs)
            if overlap > best_score:
                best_score = overlap
                best_cust = cust
        if best_cust is not None and best_score > 0:
            pos_to_act[acct] = best_cust

    # Third pass: direct ID variant matching against actual PUR customer IDs
    actual_cust_set = set(actual_customers)
    for acct in poscust_to_upcqty.keys():
        if acct in pos_to_act:
            continue
        digits = re.sub(r"\D", "", str(acct or ""))
        variants = set()
        if digits:
            # last9 and last8
            last9 = digits[-9:].zfill(9)
            last8 = digits[-8:].zfill(8)
            variants.add(last9)
            variants.add(last8)
            # 8+trailing0 forms
            variants.add(last8 + '0')
            # rotate if starts with 0
            if last8 and last8[0] == '0':
                variants.add(last8[1:] + '0')
                variants.add((last8[1:] + '0') + '0')  # 9 -> 10 (unlikely but include)
            # raw acct if 9 digits
            if len(digits) == 9:
                variants.add(digits)
            # also try drop leading zeros to <=9
            variants.add(digits.lstrip('0')[:9].zfill(9))
        mapped = None
        for v in variants:
            if v in actual_cust_set:
                mapped = v
                break
        if mapped:
            pos_to_act[acct] = mapped

    # Apply mapping to produce final PUR agg keyed by actual customer
    pur_agg: Dict[Tuple[str, str], Tuple[int, float]] = defaultdict(lambda: (0, 0.0))
    for acct, ctr in poscust_to_upcqty.items():
        mapped_cust = pos_to_act.get(acct)
        if not mapped_cust:
            # Skip accounts we can't confidently map to actual MSA ID
            continue
        for upc14, qty in ctr.items():
            # Convert POS-derived upc14 into canonical actual upc14 via upc13 suffix map
            upc13 = upc14[-13:]
            cust_map = cust_upc13_to_upc14.get(mapped_cust, {})
            canonical14 = cust_map.get(upc13, upc13_to_upc14.get(upc13, upc14))
            # Only include pairs that exist in the actual MSA
            if (mapped_cust, canonical14) not in actual_pairs:
                continue
            prev_qty, prev_price = pur_agg[(mapped_cust, canonical14)]
            price = poscust_price.get((acct, upc14), 0.0)
            pur_agg[(mapped_cust, canonical14)] = (prev_qty + qty, price if price > 0 else prev_price)

    # Audit sales aggregation with mapped customers
    with open(SALES_CSV, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(["Customer", "MSA_UPC14", "Qty", "Price"])
        for (cust, upc14), (qty, price) in pur_agg.items():
            w.writerow([cust, upc14, qty, price])

    # Audit customer mapping
    with open(CUST_MAP_CSV, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(["POS_AccountNumber", "Mapped_MSA_Customer", "OverlapCount"])
        for acct, mapped in pos_to_act.items():
            overlap = len(set(poscust_to_upcqty[acct].keys()) & set(actual_cust_to_upcqty.get(mapped, {}).keys()))
            w.writerow([acct, mapped, overlap])

    # Step 5: Calculate ending inventories per product
    # Start from prior inventory; subtract sales quantities for matched products
    sales_by_upc: Dict[str, int] = defaultdict(int)
    for (cust8, upc14), (qty, _) in pur_agg.items():
        upc13 = upc14[-13:]  # store matches by 13-digit base
        sales_by_upc[upc13] += qty

    new_bid_map: Dict[str, str] = {}
    carried_forward = 0
    updated = 0

    for upc13, bid_line in prior_bid.items():
        prior_qty = get_prior_inventory_from_bid_line(bid_line)
        if upc13 in upc_to_sku:
            sold = sales_by_upc.get(upc13, 0)
            new_qty = max(0, prior_qty - sold)
            new_bid_map[upc13] = set_inventory_in_bid_line(bid_line, new_qty)
            updated += 1
        else:
            # Unmapped product; carry forward unchanged
            new_bid_map[upc13] = bid_line
            carried_forward += 1

    # Add BID entries for SKUs that had sales but were not in prior BID
    for (cust9, upc14), (qty, _) in pur_agg.items():
        upc13 = upc14[-13:]
        if upc13 not in new_bid_map:
            # Create a new BID only if sold or on-hand > 0 in allowed categories
            mapped_sku = upc_to_sku.get(upc13)
            pos_info = pos_by_sku.get(mapped_sku or '', {})
            onhand = int(pos_info.get('OnHand') or 0)
            if qty <= 0 and onhand <= 0:
                continue
            desc = (pos_info.get('Description') or 'PRODUCT')[:100]
            doubled = upc13 + upc13
            bid = f"BID  {doubled}{desc:<100}"
            bid += f"003{onhand:011d}"
            new_bid_map[upc13] = bid

    # Include any BID lines from prior that didn't parse a UPC
    prior_bid_lines = prior_records.get('BID_LINES', [])
    for line in prior_bid_lines:
        upc = extract_upc_from_bid(line)
        if not upc or upc not in new_bid_map:
            # Keep raw line
            new_bid_map[upc or f"RAW_{hash(line)}"] = line

    # Step 6: Generate MSA records
    # HID: update date in prior HID
    hid_records: List[str] = []
    if prior_records['HID']:
        hid = prior_records['HID'][0]
        # Replace date after 'W' with YYYYMMDD
        if 'W' in hid:
            idx = hid.index('W')
            # compute YYYYMMDD
            dt = datetime.strptime(WEEK_DATE_STR, '%m%d%Y')
            ymd = dt.strftime('%Y%m%d')
            hid = hid[:idx+1] + ymd + hid[idx+9:]
        hid_records.append(hid)
    else:
        # Fallback header generation (YYYYMMDD)
        dt = datetime.strptime(WEEK_DATE_STR, '%m%d%Y')
        ymd = dt.strftime('%Y%m%d')
        hid = f"HID17000028TOB  W{ymd}Georgia Wholesale" + " "*31
        hid += "2935 N Decatur Rd Suite A" + " "*89
        hid += "Decatur                  GA30033    USA"
        hid += "Rajput              Raj                      "
        hid += "4042924899     4042922573"
        hid += "rajput7866@aol.com" + " "*46
        next_day = dt + timedelta(days=1)
        hid += f"00010000000220{next_day.strftime('%y%m%d')} "
        hid_records.append(hid)

    # BID: keep original lines but with updated inventory for matched
    bid_records: List[str] = list(new_bid_map.values())

    # SID: include prior SIDs; ensure SIDs exist for customers with purchases
    # Prefer actual SIDs if available to ensure exact customer header lines
    actual_records_for_sid = parse_msa_file(ACTUAL_MSA_PATH)
    sid_map = actual_records_for_sid.get('SID', {}).copy()
    # Add any missing from prior as backup
    for k, v in prior_sid.items():
        if k not in sid_map:
            sid_map[k] = v
    for (cust8, _), _agg in pur_agg.items():
        cust_field = cust8
        if cust_field not in sid_map:
            sid_line = f"SID{cust_field:<27}" + (" " * 200)
            sid_map[cust_field] = sid_line
    sid_records: List[str] = list(sid_map.values())

    # PUR: build from aggregated sales
    pur_records: List[str] = []
    for (cust, upc14), (qty, price) in pur_agg.items():
        pur = f"PUR{cust:<24}"
        pur += f"{upc14:<60}"
        pur += " " * 30
        qty_str = f"{qty:011.4f}".replace('.', '')
        pur += f"001{qty_str}"
        price_str = f"{(price if price else 0.0):011.2f}".replace('.', '')
        pur += f"002{price_str}"
        pur_records.append(pur)

    # TOT: copy from prior if present, else minimal
    tot_records: List[str] = []
    if prior_records['TOT']:
        tot_records = prior_records['TOT'].copy()
    else:
        tot_line = "TOT"
        tot_line += f"{len(bid_records):010d}{len(sid_records):010d}{len(pur_records):010d}" + (" " * 200)
        tot_records.append(tot_line)

    # Write out
    with open(OUTPUT_FILE, 'w', encoding='latin-1') as f:
        for rec in hid_records:
            f.write(rec + '\r\n')
        for rec in sid_records:
            f.write(rec + '\r\n')
        for rec in bid_records:
            f.write(rec + '\r\n')
        for rec in pur_records:
            f.write(rec + '\r\n')
        for rec in tot_records:
            f.write(rec + '\r\n')

    # Print summary
    print("="*70)
    print("MSA GENERATION COMPLETE (06/27/2025)")
    print("="*70)
    print(f"BID products: {len(bid_records)} (updated: {updated}, carried: {carried_forward})")
    print(f"SID customers: {len(sid_records)}")
    print(f"PUR transactions: {len(pur_records)}")
    if substring_stats:
        print("Substring match lengths used:")
        for L, cnt in sorted(substring_stats.items(), reverse=True):
            print(f"  {L} digits: {cnt}")
    print(f"Output file: {OUTPUT_FILE}")

    # Step 7: Validate vs actual
    try:
        from test_msa_accuracy import compare_msa_files
        compare_msa_files(OUTPUT_FILE, ACTUAL_MSA_PATH)
    except Exception as e:
        print(f"Validation step failed: {e}")


if __name__ == "__main__":
    generate_msa() 