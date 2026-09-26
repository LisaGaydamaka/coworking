import math, numpy as np
import matplotlib.pyplot as plt

B,F,R,L=10/24,9.,30,2
RHOS=np.linspace(.01,.16,16)
N,WARM,SEED=1_500_000,50_000,7

def pois(mu):
    p=[math.exp(-mu)]
    while sum(p)<1-1e-14: p.append(p[-1]*mu/len(p))
    p[-1]+=1-sum(p); return np.array(p)

def analytical(lam):
    S=[(L,0)]+[(l,k) for k in range(1,R+1) for l in range(L+1)]; I={x:i for i,x in enumerate(S)}
    P=np.zeros((len(S),len(S))); pb,pf=pois(lam*B),pois(lam*F)
    for i,(l,k) in enumerate(S):
        p,C=(pf,R) if l==L else (pb,R+1)
        for a,pa in enumerate(p):
            m=min(a,C-k)
            if l==L: k2=k+m; d=(L,0) if k2==0 else (0,k2)
            else:
                k2=k+m-1; d=(L,0) if k2==0 else ((L,k2) if l+1==L else (l+1,k2))
            P[i,I[d]]+=pa
    A=P.T-np.eye(len(S)); A[-1]=1; y=np.zeros(len(S)); y[-1]=1
    q=np.linalg.solve(A,y); Tbar=area=blocked=0.
    for qi,(l,k) in zip(q,S):
        T,C,p=(F,R,pf) if l==L else (B,R+1,pb); Tbar+=qi*T
        for a,pa in enumerate(p):
            m=min(a,C-k)
            area+=qi*pa*T*(k+m-m*(m+1)/(2*(a+1))); blocked+=qi*pa*(a-m)
    pi=blocked/(lam*Tbar)
    return area/Tbar/(lam*(1-pi))

def simulate(lam,seed):
    g=np.random.default_rng(seed); l=L; k=0; t=area=arr=blk=0.
    for e in range(N+WARM):
        T,C=(F,R) if l==L else (B,R+1); a=g.poisson(lam*T); m=min(a,C-k)
        if e>=WARM:
            u=np.sort(g.random(a))[:m] if m else ()
            area+=k*T+sum(T*(1-x) for x in u); t+=T; arr+=a; blk+=a-m
        if l==L: k+=m; l=L if k==0 else 0
        else: k+=m-1; l=L if k==0 or l+1==L else l+1
    return area/t/(lam*(1-blk/arr))

ana=np.array([analytical(r/B) for r in RHOS])
sim=np.array([simulate(r/B,SEED+i) for i,r in enumerate(RHOS)])
err=abs((sim-ana)/ana)*100
data=np.c_[RHOS,ana,sim,err]
np.savetxt("results.csv",data,delimiter=",",header="rho,analytic_ms,simulation_ms,error_percent",comments="")
print("max relative error: %.2f%%"%err.max())

plt.plot(RHOS,ana,label="Analytical")
plt.plot(RHOS,sim,"o",ms=4,label="Monte Carlo")
plt.xlabel(r"$\rho=\lambda m_B$"); plt.ylabel("Mean delay, ms")
plt.grid(alpha=.3); plt.legend(); plt.tight_layout(); plt.savefig("comparison.svg")
