WITH clean AS (
 SELECT * FROM ecommerce_transactions
 WHERE customerid IS NOT NULL AND quantity>0 AND unitprice>0 AND invoiceno NOT LIKE 'C%'
), customer AS (
 SELECT customerid,
        MAX(invoicedate)::date AS last_purchase,
        MIN(invoicedate)::date AS first_purchase,
        COUNT(DISTINCT invoiceno) AS frequency,
        SUM(quantity*unitprice) AS monetary,
        SUM(quantity) AS total_quantity
 FROM clean GROUP BY customerid
), final AS (
 SELECT *, (MAX(last_purchase) OVER () + INTERVAL '1 day')::date-last_purchase AS recency_days,
        EXTRACT(DAY FROM last_purchase-first_purchase) AS lifetime_days
 FROM customer
)
SELECT customerid, recency_days AS recency, frequency, ROUND(monetary,2) monetary,
       total_quantity, first_purchase, last_purchase, lifetime_days,
       ROUND(monetary/NULLIF(frequency,0),2) AS average_order_value
FROM final ORDER BY monetary DESC;
