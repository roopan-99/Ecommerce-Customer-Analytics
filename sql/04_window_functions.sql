WITH orders AS (
 SELECT customerid, invoiceno, MIN(invoicedate) order_date,
        ROW_NUMBER() OVER(PARTITION BY customerid ORDER BY MIN(invoicedate)) AS order_number,
        DENSE_RANK() OVER(ORDER BY SUM(quantity*unitprice) DESC) AS order_value_rank
 FROM ecommerce_transactions
 WHERE customerid IS NOT NULL AND quantity>0 AND unitprice>0 AND invoiceno NOT LIKE 'C%'
 GROUP BY customerid,invoiceno
), gaps AS (
 SELECT *, LAG(order_date) OVER(PARTITION BY customerid ORDER BY order_date) previous_order_date
 FROM orders
)
SELECT *, EXTRACT(DAY FROM order_date-previous_order_date) AS days_since_previous_order FROM gaps ORDER BY customerid, order_date;
