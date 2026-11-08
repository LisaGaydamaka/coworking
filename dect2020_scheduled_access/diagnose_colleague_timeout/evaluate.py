"""Compare exact vs 1-microsecond ACK timeout against colleague's .sca counters at p=.02."""
from pathlib import Path
import csv
DATA={1:(1415,460,773,557),2:(1410,455,794,577),3:(1370,392,870,588),
      4:(1360,366,961,629),5:(1345,355,987,636),6:(1352,363,952,626),
      7:(1396,443,856,594),8:(1404,438,790,589),9:(1386,427,866,587),
      10:(1360,368,986,623)}
FIELDS=('attempts','collisions','lbt_busy','delivered')
rows=[]
for typ in ('exact','offset'):
 for seed in range(1,11):
  vals={}
  for line in (Path('results')/f'{typ}_seed_{seed}.sca').read_text().splitlines():
   x=line.split()
   if len(x)>=4 and x[0]=='scalar': vals[x[1]+'.'+x[2]]=float(x[3])
  got=(int(vals['Cluster.medium.dataTransmissionAttempts']),
       int(vals['Cluster.medium.collidedDataAttempts']),
       int(vals['Cluster.medium.busyLbtResponses']),
       int(vals['Cluster.ft.deliveredUniquePackets']))
  ref=DATA[seed]
  row=dict(timeout=typ,seed=seed,**dict(zip(FIELDS,got)),
           matches_colleague=got==ref,
           absolute_counter_error=sum(abs(a-b) for a,b in zip(got,ref)))
  rows.append(row)
with open('diagnostic.csv','w',newline='') as f:
 writer=csv.DictWriter(f,fieldnames=rows[0].keys());writer.writeheader();writer.writerows(rows)
for typ in ('exact','offset'):
 rr=[x for x in rows if x['timeout']==typ]
 print(typ,'exact matching seeds',[r['seed'] for r in rr if r['matches_colleague']],
       'sum integer error',sum(r['absolute_counter_error'] for r in rr))
for seed in range(1,11):
 print(seed,'colleague',DATA[seed],
       'exact',tuple(next(r[k] for r in rows if r['timeout']=='exact' and r['seed']==seed) for k in FIELDS),
       'offset',tuple(next(r[k] for r in rows if r['timeout']=='offset' and r['seed']==seed) for k in FIELDS))
