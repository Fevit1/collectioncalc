-- eBay Sales Migration
-- Run this on your Render Postgres database

CREATE TABLE IF NOT EXISTS ebay_sales (
    id SERIAL PRIMARY KEY,
    raw_title TEXT NOT NULL,
    parsed_title TEXT,
    issue_number VARCHAR(20),
    publisher VARCHAR(100),
    sale_price DECIMAL(10, 2) NOT NULL,
    sale_date DATE,
    condition VARCHAR(50),
    graded BOOLEAN DEFAULT FALSE,
    grade DECIMAL(3, 1),
    listing_url TEXT,
    image_url TEXT,
    ebay_item_id VARCHAR(50) UNIQUE,
    content_hash VARCHAR(64) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_ebay_sales_parsed_title ON ebay_sales(parsed_title);
CREATE INDEX IF NOT EXISTS idx_ebay_sales_issue ON ebay_sales(issue_number);
CREATE INDEX IF NOT EXISTS idx_ebay_sales_sale_date ON ebay_sales(sale_date);
CREATE INDEX IF NOT EXISTS idx_ebay_sales_publisher ON ebay_sales(publisher);
CREATE INDEX IF NOT EXISTS idx_ebay_sales_graded ON ebay_sales(graded);

-- View for FMV calculations
CREATE OR REPLACE VIEW comic_fmv AS
SELECT 
    parsed_title,
    issue_number,
    publisher,
    graded,
    COUNT(*) as sale_count,
    AVG(sale_price) as avg_price,
    MIN(sale_price) as min_price,
    MAX(sale_price) as max_price,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY sale_price) as median_price,
    MAX(sale_date) as latest_sale
FROM ebay_sales
WHERE sale_date > CURRENT_DATE - INTERVAL '90 days'
GROUP BY parsed_title, issue_number, publisher, graded;
