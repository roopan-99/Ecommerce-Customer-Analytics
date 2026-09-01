WITH clean AS (
 SELECT customerid, invoicedate::date invoice_date
 FROM ecommerce_transactions WHERE customerid IS NOT NULL AND quantity>0 AND unitprice>0 AND invoiceno NOT LIKE 'C%'
), monthly AS (
 SELECT DISTINCT customerid, DATE_TRUNC('month',invoice_date)::date order_month FROM clean
), cohorts AS (
 SELECT customerid, MIN(order_month) cohort_month FROM monthly GROUP BY customerid
), activity AS (
 SELECT m.customerid,c.cohort_month,m.order_month,
        (EXTRACT(YEAR FROM m.order_month)-EXTRACT(YEAR FROM c.cohort_month))*12+
        (EXTRACT(MONTH FROM m.order_month)-EXTRACT(MONTH FROM c.cohort_month)) AS cohort_index
 FROM monthly m JOIN cohorts c USING(customerid)
), counts AS (
 SELECT cohort_month, cohort_index, COUNT(DISTINCT customerid) active_customers FROM activity GROUP BY 1,2
), sizes AS (SELECT cohort_month, active_customers cohort_size FROM counts WHERE cohort_index=0)
SELECT c.cohort_month,c.cohort_index,c.active_customers,s.cohort_size,
       ROUND(100.0*c.active_customers/s.cohort_size,2) retention_pct
FROM counts c JOIN sizes s USING(cohort_month) ORDER BY 1,2;
