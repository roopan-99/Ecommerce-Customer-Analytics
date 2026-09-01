-- 1. Highest value customers
SELECT customerid,SUM(quantity*unitprice) revenue FROM ecommerce_transactions WHERE customerid IS NOT NULL AND quantity>0 GROUP BY customerid ORDER BY revenue DESC LIMIT 20;
-- 2. Country performance
SELECT country,SUM(quantity*unitprice) revenue,COUNT(DISTINCT invoiceno) orders,COUNT(DISTINCT customerid) customers FROM ecommerce_transactions WHERE quantity>0 GROUP BY country ORDER BY revenue DESC;
-- 3. Monthly revenue trend
SELECT DATE_TRUNC('month',invoicedate)::date month,SUM(quantity*unitprice) revenue,COUNT(DISTINCT invoiceno) orders FROM ecommerce_transactions WHERE quantity>0 GROUP BY 1 ORDER BY 1;
-- 4. Repeat purchase rate
WITH f AS (SELECT customerid,COUNT(DISTINCT invoiceno) orders FROM ecommerce_transactions WHERE customerid IS NOT NULL AND quantity>0 GROUP BY customerid) SELECT ROUND(100.0*AVG((orders>1)::int),2) repeat_customer_pct FROM f;
