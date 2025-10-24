#!/usr/bin/env python3

import re
import csv
from collections import defaultdict

GENERATED_AUDIT_CSV = "archive/data_exports/msa_06272025_audit_sales.csv"
ACTUAL_MSA_FILE = "MSA Data Fr/06272025"
GENERATED_MSA_FILE = "generated_06272025.txt"


def parse_actual_pur_pairs(filepath):
    pairs = set()
    with open(filepath, 'r', encoding='latin-1') as f:
        for line in f:
            if not line.startswith('PUR'):
                continue
            cust = line[3:27].strip()
            upc_match = re.search(r"(\d{14})", line[27:])
            if not upc_match:
                continue
            upc14 = upc_match.group(1)
            pairs.add((cust, upc14))
    return pairs


def parse_generated_pur_pairs(filepath):
    pairs = set()
    with open(filepath, 'r', encoding='latin-1') as f:
        for line in f:
            if not line.startswith('PUR'):
                continue
            cust = line[3:27].strip()
            upc_match = re.search(r"(\d{14})", line[27:])
            if not upc_match:
                continue
            upc14 = upc_match.group(1)
            pairs.add((cust, upc14))
    return pairs


def parse_actual_pur(filepath):
    agg = defaultdict(int)
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
            agg[(cust, upc14)] += qty
    return agg


def parse_generated_audit(csv_path):
    agg = {}
    with open(csv_path, 'r', newline='') as f:
        r = csv.DictReader(f)
        # Support either Customer or Customer9
        cust_col = 'Customer' if 'Customer' in r.fieldnames else 'Customer9'
        upc_col = 'MSA_UPC14'
        for row in r:
            cust = str(row[cust_col]).strip()
            upc14 = str(row[upc_col]).strip()
            qty = int(row['Qty']) if row.get('Qty') else 0
            agg[(cust, upc14)] = agg.get((cust, upc14), 0) + qty
    return agg


def main():
    # Pair-only overlap
    act_pairs = parse_actual_pur_pairs(ACTUAL_MSA_FILE)
    gen_pairs = parse_generated_pur_pairs(GENERATED_MSA_FILE)

    inter_pairs = act_pairs & gen_pairs
    print("="*70)
    print("PAIR OVERLAP (ignoring qty/price)")
    print("="*70)
    print(f"Generated pairs: {len(gen_pairs)}  Actual pairs: {len(act_pairs)}  Intersection: {len(inter_pairs)}")

    # Totals by CSV audit and actual quantities
    gen = parse_generated_audit(GENERATED_AUDIT_CSV)
    act = parse_actual_pur(ACTUAL_MSA_FILE)

    gen_keys = set(gen.keys())
    act_keys = set(act.keys())

    inter = gen_keys & act_keys
    missing = act_keys - gen_keys
    extra = gen_keys - act_keys

    total_gen_qty = sum(gen[k] for k in gen_keys)
    total_act_qty = sum(act[k] for k in act_keys)
    total_inter_gen = sum(gen[k] for k in inter)
    total_inter_act = sum(act[k] for k in inter)

    print("\n" + "="*70)
    print("QUANTITY TOTALS (from audit)")
    print("="*70)
    print(f"Generated total qty: {total_gen_qty}")
    print(f"Actual total qty:    {total_act_qty}")
    print(f"Overlap qty (gen):   {total_inter_gen}")
    print(f"Overlap qty (act):   {total_inter_act}")

    # Customer-only and UPC-only coverage
    gen_customers = set(c for (c, _) in gen_pairs)
    act_customers = set(c for (c, _) in act_pairs)
    gen_upcs = set(u for (_, u) in gen_pairs)
    act_upcs = set(u for (_, u) in act_pairs)

    print("\n" + "="*70)
    print("COVERAGE by dimension")
    print("="*70)
    print(f"Customers: gen={len(gen_customers)} act={len(act_customers)} overlap={len(gen_customers & act_customers)}")
    print(f"UPCs:      gen={len(gen_upcs)} act={len(act_upcs)} overlap={len(gen_upcs & act_upcs)}")

    if inter_pairs:
        print("\nSample matching pairs:")
        for i, k in enumerate(list(inter_pairs)[:10]):
            print(f"  {k[0]} | {k[1]}")
    else:
        print("\nNo exact (customer, upc) pair matches yet.")

if __name__ == "__main__":
    main() 