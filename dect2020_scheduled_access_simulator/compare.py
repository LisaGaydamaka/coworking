import math
from collections import deque
import numpy as np
import matplotlib.pyplot as plt

MU,F,R,L=2.4,9.0,30,2
RHOS=np.array([.01,.03,.05,.07,.08,.09,.10,.12,.15,.20,.30,.50,1.,1.5,2.5])
SEED,WARM=7,10_000

def states():
    return [(L,0)]+[(l,k) for l in range(L+1) for k in range(1,R+1)]

def transition(lam):
    S=states(); I={s:i for i,s in enumerate(S)}; P=np.zeros((len(S),len(S)))
    p=lam/(lam+MU); q=1-p
    for i,(l,k) in enumerate(S):
        if l==L:                         # type-2 service: deterministic F
            m=lam*F; cap=R-k; probs=[]
            if cap:
                x=math.exp(-m); probs=[x]
                for a in range(1,cap): x*=m/a; probs.append(x)
            for a,pa in enumerate(probs):
                k2=k+a; P[i,I[(L,0) if k2==0 else (0,k2)]]+=pa
            tail=1-sum(probs)
            P[i,I[(L,0) if R==0 else (0,R)]]+=tail
        else:                            # type-1 service: Exp(MU)
            cap=R+1-k; probs=[q*p**a for a in range(cap)]
            for a,pa in enumerate(probs):
                k2=k-1+a
                d=(L,0) if k2==0 else ((L,k2) if l+1==L else (l+1,k2))
                P[i,I[d]]+=pa
            tail=1-sum(probs); k2=R
            d=(L,0) if k2==0 else ((L,k2) if l+1==L else (l+1,k2))
            P[i,I[d]]+=tail
    return S,P

def fixed_reward(lam,k,C,T):
    s=C-k
    if s<=0: return C*T,lam*T
    x=lam*T; e=math.exp(-x); I=[]; pk=e
    I0=(1-e)/lam
    I.append(I0)
    for j in range(1,s):
        I.append(I[-1]-e*x**j/(lam*math.factorial(j)))
    area=sum((k+j)*I[j] for j in range(s))+C*(T-sum(I))
    probs=[e]
    for a in range(1,s): probs.append(probs[-1]*x/a)
    admitted=sum(a*pa for a,pa in enumerate(probs))+s*(1-sum(probs))
    return area,x-admitted

def exp_reward(lam,k,C):
    p=lam/(lam+MU)
    area=sum(n*p**d/(lam+MU) for d,n in enumerate(range(k,C)))+C*p**(C-k)/MU
    return area,(lam/MU)*p**(C-k)

def analytical(rho):
    lam=rho*MU; S,P=transition(lam)
    A=P.T-np.eye(len(P)); A[-1]=1; b=np.zeros(len(P)); b[-1]=1
    q=np.linalg.solve(A,b); H=area=blocked=0.
    for qi,(l,k) in zip(q,S):
        if l==L: T=F; a,z=fixed_reward(lam,k,R,F)
        else: T=1/MU; a,z=exp_reward(lam,k,R+1)
        H+=qi*T; area+=qi*a; blocked+=qi*z
    N=area/H; pi=blocked/(lam*H)
    return N/(lam*(1-pi)),pi

def simulate(rho,seed,n):
    lam=rho*MU; g=np.random.default_rng(seed); Q=deque()
    t=0.; arrival=g.exponential(1/lam); mode=2; end=F; cur=None; l=L
    done=kept=0; collect=False; delay=0.; arrivals=blocked=0
    while kept<n:
        if arrival<end:
            t=arrival
            if collect: arrivals+=1
            if len(Q)<R: Q.append((t,collect))
            elif collect: blocked+=1
            arrival=t+g.exponential(1/lam)
        else:
            t=end
            if mode==1:
                done+=1
                if cur[1]: delay+=t-cur[0]; kept+=1
                l+=1
                if not collect and done>=WARM: collect=True
                if not Q or l==L: mode=2; cur=None; end=t+F
                else: cur=Q.popleft(); end=t+g.exponential(1/MU)
            else:
                l=0
                if Q: mode=1; cur=Q.popleft(); end=t+g.exponential(1/MU)
                else: end=t+F
    return delay/kept,blocked/arrivals

ana=[]; sim=[]; api=[]; spi=[]
for i,rho in enumerate(RHOS):
    a,p=analytical(rho)
    n=500_000 if .07<=rho<=.10 else 150_000
    s,ps=simulate(rho,SEED+i,n)
    ana.append(a); api.append(p); sim.append(s); spi.append(ps)

ana=np.array(ana); sim=np.array(sim); err=abs(sim/ana-1)*100
np.savetxt("results.csv",np.c_[RHOS,ana,sim,err,api,spi],delimiter=",",
 header="rho,analytic_ms,simulation_ms,error_percent,analytic_blocking,simulation_blocking",comments="")
print("max delay error: %.2f%%"%err.max())

plt.plot(RHOS,ana,"-",label="Analytical (corrected)")
plt.plot(RHOS,sim,"o",ms=4,label="Monte Carlo")
plt.xlabel("rho = lambda m_B"); plt.ylabel("Mean delay, ms")
plt.grid(alpha=.3); plt.legend(); plt.tight_layout(); plt.savefig("comparison.svg")
