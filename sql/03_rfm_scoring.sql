WITH rfm AS (
 SELECT customerid,
        (MAX(invoicedate)::date - MAX(invoicedate)::date) AS dummy,
        (MAX(MAX(invoicedate)) OVER ()::date - MAX(invoicedate)::date + 1) AS recency,
        COUNT(DISTINCT invoiceno) AS frequency,
        SUM(quantity*unitprice) AS monetary
 FROM ecommerce_transactions
 WHERE customerid IS NOT NULL AND quantity>0 AND unitprice>0 AND invoiceno NOT LIKE 'C%'
 GROUP BY customerid
), scored AS (
 SELECT *,
        NTILE(5) OVER (ORDER BY recency DESC) AS r_score,
        NTILE(5) OVER (ORDER BY frequency) AS f_score,
        NTILE(5) OVER (ORDER BY monetary) AS m_score
 FROM rfm
)
SELECT *, CONCAT(r_score,f_score,m_score) AS rfm_score FROM scored ORDER BY monetary DESC;
