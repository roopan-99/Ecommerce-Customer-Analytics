-- PostgreSQL data quality checks. Load data/raw/ecommerce_transactions.csv into ecommerce_transactions.
SELECT COUNT(*) AS rows, COUNT(DISTINCT invoiceno) AS orders, COUNT(DISTINCT customerid) AS customers FROM ecommerce_transactions;
SELECT COUNT(*) AS null_customer_rows FROM ecommerce_transactions WHERE customerid IS NULL;
SELECT COUNT(*) AS duplicate_rows FROM (SELECT invoiceno, stockcode, invoicedate, customerid, quantity, unitprice, COUNT(*) c FROM ecommerce_transactions GROUP BY 1,2,3,4,5,6 HAVING COUNT(*)>1) x;
SELECT MIN(invoicedate) AS first_date, MAX(invoicedate) AS last_date, MIN(unitprice) AS min_price, MIN(quantity) AS min_qty FROM ecommerce_transactions;
SELECT COUNT(*) AS returns_or_cancellations FROM ecommerce_transactions WHERE invoiceno LIKE 'C%' OR quantity<=0;
