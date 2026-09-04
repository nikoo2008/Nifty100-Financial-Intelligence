-- Exploratory queries for nifty100.db

-- 1. Loaded row counts by table.
SELECT 'companies' AS table_name, COUNT(*) AS row_count FROM companies
UNION ALL SELECT 'profitandloss', COUNT(*) FROM profitandloss
UNION ALL SELECT 'balancesheet', COUNT(*) FROM balancesheet
UNION ALL SELECT 'cashflow', COUNT(*) FROM cashflow
UNION ALL SELECT 'analysis', COUNT(*) FROM analysis
UNION ALL SELECT 'documents', COUNT(*) FROM documents
UNION ALL SELECT 'prosandcons', COUNT(*) FROM prosandcons;

-- 2. Companies with the most profit-and-loss history.
SELECT c.id, c.company_name, COUNT(*) AS years
FROM companies c JOIN profitandloss p ON p.company_id = c.id
GROUP BY c.id, c.company_name ORDER BY years DESC, c.id LIMIT 20;

-- 3. Latest available profit and EPS by company.
SELECT c.id, c.company_name, p.year, p.net_profit, p.eps
FROM companies c JOIN profitandloss p ON p.company_id = c.id
WHERE p.year = (SELECT MAX(p2.year) FROM profitandloss p2 WHERE p2.company_id = p.company_id)
ORDER BY p.net_profit DESC LIMIT 20;

-- 4. Latest balance-sheet totals and borrowings.
SELECT c.id, c.company_name, b.year, b.total_assets, b.total_liabilities, b.borrowings
FROM companies c JOIN balancesheet b ON b.company_id = c.id
WHERE b.year = (SELECT MAX(b2.year) FROM balancesheet b2 WHERE b2.company_id = b.company_id)
ORDER BY b.total_assets DESC LIMIT 20;

-- 5. Companies with positive latest operating cash flow.
SELECT c.id, c.company_name, f.year, f.operating_activity, f.net_cash_flow
FROM companies c JOIN cashflow f ON f.company_id = c.id
WHERE f.year = (SELECT MAX(f2.year) FROM cashflow f2 WHERE f2.company_id = f.company_id)
  AND f.operating_activity > 0 ORDER BY f.operating_activity DESC LIMIT 20;

-- 6. Companies with the highest recorded ROE analysis value.
SELECT c.id, c.company_name, a.roe, a.compounded_profit_growth
FROM companies c JOIN analysis a ON a.company_id = c.id
ORDER BY CAST(REPLACE(REPLACE(a.roe, 'Last Year:', ''), '%', '') AS REAL) DESC LIMIT 20;

-- 7. Annual-report coverage by company.
SELECT c.id, c.company_name, COUNT(d.id) AS report_count, MIN(d.year) AS first_year, MAX(d.year) AS latest_year
FROM companies c LEFT JOIN documents d ON d.company_id = c.id
GROUP BY c.id, c.company_name ORDER BY report_count DESC, c.id;

-- 8. Companies with recorded pros and cons.
SELECT c.id, c.company_name, COUNT(pc.id) AS observations
FROM companies c JOIN prosandcons pc ON pc.company_id = c.id
GROUP BY c.id, c.company_name ORDER BY observations DESC;

-- 9. Latest profit margin proxy: net profit divided by sales.
SELECT c.id, c.company_name, p.year, p.sales, p.net_profit,
       ROUND(100.0 * p.net_profit / NULLIF(p.sales, 0), 2) AS net_margin_pct
FROM companies c JOIN profitandloss p ON p.company_id = c.id
WHERE p.year = (SELECT MAX(p2.year) FROM profitandloss p2 WHERE p2.company_id = p.company_id)
ORDER BY net_margin_pct DESC LIMIT 20;

-- 10. Latest-year rows where liabilities exceed assets, for investigation.
SELECT c.id, c.company_name, b.year, b.total_liabilities, b.total_assets
FROM companies c JOIN balancesheet b ON b.company_id = c.id
WHERE b.year = (SELECT MAX(b2.year) FROM balancesheet b2 WHERE b2.company_id = b.company_id)
  AND b.total_liabilities > b.total_assets ORDER BY c.id;

-- 11. Companies present in the master table but with no P&L records.
SELECT c.id, c.company_name
FROM companies c LEFT JOIN profitandloss p ON p.company_id = c.id
WHERE p.company_id IS NULL ORDER BY c.id;