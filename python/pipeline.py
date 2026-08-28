import os, numpy as np, pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import matplotlib.pyplot as plt, seaborn as sns

ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW=os.path.join(ROOT,'data','raw','ecommerce_transactions.csv')
PROC=os.path.join(ROOT,'data','processed'); OUT=os.path.join(ROOT,'outputs'); CH=os.path.join(OUT,'charts')
os.makedirs(PROC,exist_ok=True); os.makedirs(CH,exist_ok=True)

# Reproducible portfolio dataset: synthetic e-commerce transactions with realistic customer behavior.
def generate_data(n_customers=5000, n_rows=150000, seed=42):
    rng=np.random.default_rng(seed)
    start=pd.Timestamp('2024-01-01'); end=pd.Timestamp('2025-12-31')
    cust=np.arange(10001,10001+n_customers)
    # latent customer value drives frequency/spend and makes clustering meaningful
    value=rng.gamma(2.0,1.0,n_customers); value=(value-value.min())/(value.max()-value.min())
    customer=np.repeat(cust, np.ceil(n_rows/n_customers).astype(int))[:n_rows]
    idx=customer-10001
    dates=start + pd.to_timedelta(rng.integers(0,(end-start).days+1,n_rows),unit='D') + pd.to_timedelta(rng.integers(0,86400,n_rows),unit='s')
    qty=np.maximum(1,rng.poisson(2.5+3.0*value[idx])+1)
    price=np.round(np.exp(rng.normal(np.log(18+25*value[idx]),0.55)),2)
    products=rng.integers(1,401,n_rows)
    countries=rng.choice(['United Kingdom','Germany','France','Spain','Netherlands','Ireland','Belgium','Australia'],n_rows,p=[.48,.12,.10,.08,.08,.06,.05,.03])
    invoice_num=np.arange(500000,n_rows+500000)
    # add repeat-order IDs by grouping adjacent rows
    invoice_id=invoice_num//3
    desc=np.array([f'Product {p:03d}' for p in products])
    df=pd.DataFrame({'InvoiceNo':invoice_id.astype(str),'StockCode':[f'SKU{p:04d}' for p in products], 'Description':desc,
                     'Quantity':qty,'InvoiceDate':dates,'UnitPrice':price,'CustomerID':customer.astype(str),'Country':countries})
    df['Revenue']=np.round(df.Quantity*df.UnitPrice,2)
    # realistic returns/cancellations (2%) and duplicate rows (0.3%) to demonstrate cleaning
    ret_idx=rng.choice(df.index,size=int(.02*n_rows),replace=False); df.loc[ret_idx,'Quantity']=-df.loc[ret_idx,'Quantity']
    dup=df.sample(frac=.003,random_state=seed); df=pd.concat([df,dup],ignore_index=True)
    # cancellation invoice prefix for a subset of returns
    mask=df.Quantity<0; df.loc[mask,'InvoiceNo']='C'+df.loc[mask,'InvoiceNo'].astype(str)
    return df

def clean(df):
    before=len(df); dup=df.duplicated().sum(); miss=df.CustomerID.isna().sum()
    df=df.drop_duplicates().copy(); df=df.dropna(subset=['CustomerID']); df.InvoiceDate=pd.to_datetime(df.InvoiceDate)
    cancel=df.InvoiceNo.astype(str).str.startswith('C') | (df.Quantity<=0)
    canc=int(cancel.sum()); df=df[~cancel].copy(); invalid=int((df.UnitPrice<=0).sum()); df=df[df.UnitPrice>0].copy()
    df['Revenue']=df.Quantity*df.UnitPrice
    audit={'rows_before':before,'duplicates_removed':int(dup),'missing_customer_removed':int(miss),'returns_cancelled_removed':canc,'invalid_price_removed':invalid,'rows_after':len(df)}
    return df,audit

def rfm(df):
    ref=df.InvoiceDate.max()+pd.Timedelta(days=1)
    r=df.groupby('CustomerID').agg(Recency=('InvoiceDate',lambda x:(ref-x.max()).days),Frequency=('InvoiceNo','nunique'),Monetary=('Revenue','sum'),TotalQuantity=('Quantity','sum'),FirstPurchase=('InvoiceDate','min'),LastPurchase=('InvoiceDate','max'),Country=('Country',lambda x:x.mode().iat[0])).reset_index()
    r['AverageOrderValue']=r.Monetary/r.Frequency; r['LifetimeDays']=(r.LastPurchase-r.FirstPurchase).dt.days
    r['R_Score']=pd.qcut(r.Recency.rank(method='first'),5,labels=[5,4,3,2,1]).astype(int)
    r['F_Score']=pd.qcut(r.Frequency.rank(method='first'),5,labels=[1,2,3,4,5]).astype(int)
    r['M_Score']=pd.qcut(r.Monetary.rank(method='first'),5,labels=[1,2,3,4,5]).astype(int)
    r['RFM_Score']=r.R_Score.astype(str)+r.F_Score.astype(str)+r.M_Score.astype(str)
    def seg(x):
        R,F,M=x.R_Score,x.F_Score,x.M_Score
        if R>=4 and F>=4 and M>=4:return 'Champions'
        if R>=3 and F>=3:return 'Loyal Customers'
        if R>=4 and F<=2:return 'New / Promising'
        if R<=2 and F>=4:return 'Cannot Lose Them'
        if R<=2 and F>=3:return 'At Risk'
        if R==3:return 'Need Attention'
        return 'Hibernating'
    r['RFM_Segment']=r.apply(seg,axis=1)
    return r

def clustering(r):
    X=np.log1p(r[['Recency','Frequency','Monetary']].astype(float)); X=StandardScaler().fit_transform(X)
    scores=[]; inert=[]
    for k in range(2,9):
        km=KMeans(n_clusters=k,random_state=42,n_init=20).fit(X); inert.append(km.inertia_); scores.append(silhouette_score(X,km.labels_))
    best=int(np.argmax(scores))+2; km=KMeans(n_clusters=best,random_state=42,n_init=20).fit(X)
    r=r.copy(); r['KMeansCluster']=km.labels_; r['ClusterProfile']=r.groupby('KMeansCluster')['Monetary'].transform('mean')
    pd.DataFrame({'K':range(2,9),'Inertia':inert,'Silhouette':scores}).to_csv(os.path.join(PROC,'cluster_evaluation.csv'),index=False)
    fig,ax=plt.subplots(); ax.plot(range(2,9),inert,marker='o'); ax.set_title('K-Means Elbow Curve'); ax.set_xlabel('K'); ax.set_ylabel('Inertia'); fig.tight_layout(); fig.savefig(os.path.join(CH,'01_elbow.png'),dpi=150); plt.close(fig)
    fig,ax=plt.subplots(); ax.plot(range(2,9),scores,marker='o'); ax.axvline(best,ls='--'); ax.set_title('Silhouette Score by K'); ax.set_xlabel('K'); ax.set_ylabel('Silhouette'); fig.tight_layout(); fig.savefig(os.path.join(CH,'02_silhouette.png'),dpi=150); plt.close(fig)
    return r,best,max(scores)

def cohort(df):
    x=df[['CustomerID','InvoiceDate']].copy(); x['OrderMonth']=x.InvoiceDate.dt.to_period('M').dt.to_timestamp(); first=x.groupby('CustomerID').OrderMonth.min().rename('CohortMonth'); x=x.join(first,on='CustomerID'); x['CohortIndex']=(x.OrderMonth.dt.year-x.CohortMonth.dt.year)*12+(x.OrderMonth.dt.month-x.CohortMonth.dt.month)
    active=x.groupby(['CohortMonth','CohortIndex']).CustomerID.nunique().reset_index(name='ActiveCustomers'); sizes=active[active.CohortIndex==0][['CohortMonth','ActiveCustomers']].rename(columns={'ActiveCustomers':'CohortSize'}); active=active.merge(sizes,on='CohortMonth'); active['RetentionRate']=active.ActiveCustomers/active.CohortSize
    mat=active.pivot(index='CohortMonth',columns='CohortIndex',values='RetentionRate'); mat.to_csv(os.path.join(PROC,'cohort_retention_matrix.csv')); active.to_csv(os.path.join(PROC,'cohort_retention_long.csv'),index=False)
    fig,ax=plt.subplots(figsize=(12,7)); sns.heatmap(mat*100,annot=False,fmt='.1f',ax=ax,cbar_kws={'label':'Retention %'}); ax.set_title('Monthly Cohort Retention'); ax.set_xlabel('Months Since First Purchase'); ax.set_ylabel('Cohort Month'); fig.tight_layout(); fig.savefig(os.path.join(CH,'03_cohort_retention_heatmap.png'),dpi=160); plt.close(fig)
    return active

def main():
    if not os.path.exists(RAW):
        print('Generating included portfolio dataset...'); generate_data().to_csv(RAW,index=False)
    raw=pd.read_csv(RAW); clean_df,audit=clean(raw); clean_df.to_csv(os.path.join(PROC,'cleaned_transactions.csv'),index=False)
    r=rfm(clean_df); r, best, sil=clustering(r); r.to_csv(os.path.join(PROC,'customer_segments.csv'),index=False); r.to_csv(os.path.join(PROC,'rfm_customers.csv'),index=False)
    cohort_df=cohort(clean_df)
    # additional business outputs
    seg=r.groupby('RFM_Segment').agg(Customers=('CustomerID','count'),Revenue=('Monetary','sum'),AvgRecency=('Recency','mean'),AvgFrequency=('Frequency','mean'),AvgMonetary=('Monetary','mean')).sort_values('Revenue',ascending=False).reset_index(); seg['RevenueShare']=seg.Revenue/seg.Revenue.sum(); seg.to_csv(os.path.join(PROC,'segment_summary.csv'),index=False)
    country=clean_df.groupby('Country').agg(Revenue=('Revenue','sum'),Orders=('InvoiceNo','nunique'),Customers=('CustomerID','nunique')).sort_values('Revenue',ascending=False).reset_index(); country.to_csv(os.path.join(PROC,'country_summary.csv'),index=False)
    monthly=clean_df.assign(Month=clean_df.InvoiceDate.dt.to_period('M').dt.to_timestamp()).groupby('Month').agg(Revenue=('Revenue','sum'),Orders=('InvoiceNo','nunique'),Customers=('CustomerID','nunique')).reset_index(); monthly.to_csv(os.path.join(PROC,'monthly_summary.csv'),index=False)
    summary={'Raw rows':len(raw),'Clean rows':len(clean_df),'Customers':r.CustomerID.nunique(),'Orders':clean_df.InvoiceNo.nunique(),'Revenue':clean_df.Revenue.sum(),'AOV':clean_df.groupby('InvoiceNo').Revenue.sum().mean(),'Best K':best,'Best silhouette':sil,'Repeat customer rate':(r.Frequency>1).mean(),'Top segment':seg.iloc[0].RFM_Segment}
    pd.DataFrame([summary]).to_csv(os.path.join(PROC,'project_summary.csv'),index=False)
    with open(os.path.join(PROC,'data_quality_audit.txt'),'w') as f:
        f.write('\n'.join(f'{k}: {v}' for k,v in audit.items()))
    print(summary)
if __name__=='__main__': main()
