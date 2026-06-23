#!/usr/bin/env python
"""READ-ONLY sales-data coverage assessment (Section: moat investigation).
Connects with DATABASE_URL_RO (the do_readonly role), opens a READ-ONLY session,
runs ONLY SELECTs, and prints aggregate coverage numbers. No writes, no DDL.
Does not print the connection string or any row-level PII.
"""
import os, sys, io

sys.stdout.reconfigure(encoding='utf-8')  # cross-project L-2026-015

# --- load DATABASE_URL_RO from .env without printing it ---
def load_env(path=".env"):
    if not os.path.exists(path):
        return
    for line in io.open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

load_env()
dburl = os.environ.get("DATABASE_URL_RO") or os.environ.get("DATABASE_URL")
if not dburl:
    print("No DATABASE_URL_RO/DATABASE_URL in env"); sys.exit(1)

import psycopg2
conn = psycopg2.connect(dburl)
conn.set_session(readonly=True, autocommit=True)  # hard read-only
cur = conn.cursor()

def q(label, sql, params=None):
    try:
        cur.execute(sql, params or [])
        rows = cur.fetchall()
        print(f"\n### {label}")
        for r in rows:
            print("   ", r)
        return rows
    except Exception as e:
        conn.rollback() if not conn.autocommit else None
        print(f"\n### {label}\n    ERROR: {e}")
        return None

print("=" * 70)
print("SLAB WORTHY — SALES DATA COVERAGE ASSESSMENT (READ-ONLY)")
print("=" * 70)

# 0. confirm columns exist
q("ebay_sales columns",
  "SELECT column_name FROM information_schema.columns WHERE table_name='ebay_sales' ORDER BY ordinal_position")
q("market_sales columns",
  "SELECT column_name FROM information_schema.columns WHERE table_name='market_sales' ORDER BY ordinal_position")

# 1. VOLUME & BREADTH ---------------------------------------------------------
q("VOLUME: ebay_sales total rows", "SELECT count(*) FROM ebay_sales")
q("VOLUME: market_sales total rows", "SELECT count(*) FROM market_sales")
q("CHANNEL: market_sales by source", "SELECT source, count(*) FROM market_sales GROUP BY source ORDER BY 2 DESC")
q("ebay_sales graded vs raw",
  "SELECT count(*) FILTER (WHERE graded) graded, count(*) FILTER (WHERE graded IS NOT TRUE) raw_or_null FROM ebay_sales")
q("ebay_sales canonical_title NULL/empty (dead for valuation matching)",
  "SELECT count(*) FILTER (WHERE canonical_title IS NULL OR canonical_title='') as no_canon, count(*) total FROM ebay_sales")
q("BREADTH: ebay distinct (canonical_title, issue_number) keys",
  "SELECT count(*) FROM (SELECT DISTINCT canonical_title, issue_number FROM ebay_sales WHERE canonical_title IS NOT NULL AND canonical_title<>'') x")
q("BREADTH: market distinct (coalesce(canonical_title,title), issue) keys",
  "SELECT count(*) FROM (SELECT DISTINCT COALESCE(canonical_title,title) t, issue FROM market_sales WHERE COALESCE(canonical_title,title) IS NOT NULL) x")

# 2. DEPTH --------------------------------------------------------------------
q("DEPTH (ALL ebay rows by canonical_title+issue): histogram + percentiles",
  """WITH keys AS (
        SELECT canonical_title, issue_number, count(*) c
        FROM ebay_sales WHERE canonical_title IS NOT NULL AND canonical_title<>''
        GROUP BY 1,2)
     SELECT count(*) total_keys,
            count(*) FILTER (WHERE c<=2) thin_1_2,
            count(*) FILTER (WHERE c BETWEEN 3 AND 9) mid_3_9,
            count(*) FILTER (WHERE c>=10) solid_10plus,
            round(percentile_cont(0.5) WITHIN GROUP (ORDER BY c)::numeric,1) median,
            round(percentile_cont(0.9) WITHIN GROUP (ORDER BY c)::numeric,1) p90,
            max(c) max_comps
     FROM keys""")

q("DEPTH (VALUATION-ELIGIBLE: graded, fresh<=365d, not variant/lot/reprint): histogram",
  """WITH keys AS (
        SELECT canonical_title, issue_number, count(*) c
        FROM ebay_sales
        WHERE canonical_title IS NOT NULL AND canonical_title<>''
          AND graded=true AND grade IS NOT NULL AND sale_price>5
          AND (is_variant IS NULL OR is_variant=false)
          AND (is_lot IS NULL OR is_lot=false)
          AND (is_reprint IS NULL OR is_reprint=false)
          AND COALESCE(sale_date, created_at) > NOW() - INTERVAL '365 days'
        GROUP BY 1,2)
     SELECT count(*) total_keys,
            count(*) FILTER (WHERE c<=2) thin_1_2,
            count(*) FILTER (WHERE c BETWEEN 3 AND 9) mid_3_9,
            count(*) FILTER (WHERE c>=10) solid_10plus,
            round(percentile_cont(0.5) WITHIN GROUP (ORDER BY c)::numeric,1) median,
            max(c) max_comps
     FROM keys""")

# 3. FRESHNESS ----------------------------------------------------------------
q("FRESHNESS: ebay_sales by SALE date (cumulative windows)",
  """SELECT count(*) total,
            count(*) FILTER (WHERE sale_date > NOW()-INTERVAL '90 days') le90,
            count(*) FILTER (WHERE sale_date > NOW()-INTERVAL '180 days') le180,
            count(*) FILTER (WHERE sale_date > NOW()-INTERVAL '365 days') le365,
            count(*) FILTER (WHERE sale_date IS NULL) null_saledate,
            min(sale_date)::date min_sale, max(sale_date)::date max_sale
     FROM ebay_sales""")
q("CAPTURE ACTIVITY: ebay_sales by CREATED_AT (when WE ingested)",
  """SELECT count(*) FILTER (WHERE created_at > NOW()-INTERVAL '7 days') last7,
            count(*) FILTER (WHERE created_at > NOW()-INTERVAL '30 days') last30,
            count(*) FILTER (WHERE created_at > NOW()-INTERVAL '90 days') last90,
            max(created_at)::date max_created
     FROM ebay_sales""")
q("FRESHNESS: market_sales by SOLD date + capture",
  """SELECT count(*) total,
            count(*) FILTER (WHERE sold_at > NOW()-INTERVAL '180 days') le180,
            count(*) FILTER (WHERE sold_at IS NULL) null_sold,
            max(sold_at)::date max_sold,
            count(*) FILTER (WHERE created_at > NOW()-INTERVAL '30 days') ingested_last30,
            max(created_at)::date max_created
     FROM market_sales""")

# 4. GAPS (demand vs coverage) ------------------------------------------------
q("GAPS: search_cache (eBay lookup cache) thin/no-data proxy",
  """SELECT count(*) cached_searches,
            count(*) FILTER (WHERE num_sales=0 OR num_sales IS NULL) zero,
            count(*) FILTER (WHERE num_sales BETWEEN 1 AND 2) thin_1_2,
            count(*) FILTER (WHERE num_sales>=3) ok_3plus,
            max(cached_at)::date max_cached
     FROM search_cache""")
q("GAPS: request_logs volume for valuation/fmv endpoints (are lookups even logged?)",
  """SELECT endpoint, count(*) FROM request_logs
     WHERE endpoint ILIKE '%sales/valuation%' OR endpoint ILIKE '%sales/fmv%'
     GROUP BY endpoint ORDER BY 2 DESC""")

# 5. PROCESSING vs COVERAGE (filtered-out comps) ------------------------------
q("PROCESSING: ebay_sales rows excluded by variant/lot/reprint flags",
  """SELECT count(*) FILTER (WHERE is_variant) variant,
            count(*) FILTER (WHERE is_reprint) reprint,
            count(*) FILTER (WHERE is_lot) lot,
            count(*) FILTER (WHERE is_variant OR is_reprint OR is_lot) any_excluded,
            count(*) total
     FROM ebay_sales""")
q("PROCESSING: graded+fresh VARIANTS excluded from priced pool (sitting-on-data)",
  """SELECT count(*) graded_fresh_variants
     FROM ebay_sales
     WHERE graded=true AND grade IS NOT NULL AND sale_price>5
       AND is_variant=true
       AND (is_lot IS NULL OR is_lot=false) AND (is_reprint IS NULL OR is_reprint=false)
       AND COALESCE(sale_date, created_at) > NOW() - INTERVAL '365 days'""")
q("PROCESSING: how many distinct titles have variant comps we exclude",
  """SELECT count(*) FROM (
        SELECT DISTINCT canonical_title, issue_number FROM ebay_sales
        WHERE is_variant=true AND canonical_title IS NOT NULL AND canonical_title<>''
     ) x""")

cur.close(); conn.close()
print("\n" + "=" * 70 + "\nDONE (read-only).")
