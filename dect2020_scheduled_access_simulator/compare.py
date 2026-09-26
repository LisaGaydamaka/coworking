import math, numpy as np
import matplotlib.pyplot as plt

B, F, R, L = 10/24, 9.0, 30, 2       # ms, paper baseline
RHOS = np.linspace(.01, .16, 16)      # stability/transition region
N_EVENTS, WARM = 1_500_000, 50_000
SEED = 7

def pois(mu, eps=1e-14):
    p=[math.exp(-mu)]
    while sum(p) < 1-eps:
        p.append(p[-1]*mu/len(p))
    p[-1] += 1-sum(p)
    return np.array(p)

def states():
    s=[(L,0)]+[(l,k) for k in range(1,R+1) for l in range(L+1)]
    return s,{x:i for i,x in enumerate(s)}

def analytical(lam):
    s,ix=states(); P=np.zeros((len(s),len(s)))
    pb,pf=pois(lam*B),pois(lam*F)
    for i,(l,k) in enumerate(s):
        p,T,C=(pf,F,R) if l==L else (pb,B,R+1)
        for a,pa in enumerate(p):
            m=min(a,C-k)
            if l==L:
                k2=k+m; d=(L,0) if k2==0 else (0,k2)
            else:
                k2=k+m-1
                d=(L,0) if k2==0 else ((L,k2) if l+1==L else (l+1,k2))
            P[i,ix[d]] += pa
    A=P.T-np.eye(len(s)); A[-1]=1
    y=np.zeros(len(s)); y[-1]=1
    q=np.linalg.solve(A,y)

    Tbar=Narea=blocked=0.
    for qi,(l,k) in zip(q,s):
        T,C,p=(F,R,pf) if l==L else (B,R+1,pb)
        Tbar += qi*T
        ea=eb=0.
        for a,pa in enumerate(p):
            m=min(a,C-k)
            ea += pa*T*(k+m-m*(m+1)/(2*(a+1)))
            eb += pa*(a-m)
        Narea += qi*ea; blocked += qi*eb
    N=Narea/Tbar; pi=blocked/(lam*Tbar)
    return N/(lam*(1-pi))

def simulate(lam, seed):
    g=np.random.default_rng(seed); l=L; k=0
    t=area=arr=blk=0.
    for e in range(N_EVENTS+WARM):
        T,C=(F,R) if l==L else (B,R+1)
        a=g.poisson(lam*T); m=min(a,C-k)
        if e>=WARM:
            u=np.sort(g.random(a))[:m] if m else []
            area += k*T + sum(T*(1-x) for x in u)
            t += T; arr += a; blk += a-m
        if l==L:
            k += m; l=L if k==0 else 0
        else:
            k += m-1; l=L if (k==0 or l+1==L) else l+1
    N=area/t; pi=blk/arr
    return N/(lam*(1-pi))

ana=[]; sim=[]
for i,rho in enumerate(RHOS):
    lam=rho/B
    ana.append(analytical(lam))
    sim.append(simulate(lam,SEED+i))

err=np.abs((np.array(sim)-ana)/ana)*100
print("rho   analytic_ms  simulation_ms  error_%")
for x,a,s,e in zip(RHOS,ana,sim,err):
    print(f"{x:.2f}   {a:11.4f}  {s:13.4f}  {e:7.3f}")
print(f"\nmax relative error: {err.max():.2f}%")

plt.plot(RHOS,ana,"-",label="Analytical")
plt.plot(RHOS,sim,"o",ms=4,label="Monte Carlo")
plt.xlabel(r"$\\rho=\\lambda m_B$")
plt.ylabel("Mean delay, ms")
plt.grid(alpha=.3); plt.legend(); plt.tight_layout()
plt.savefig("comparison.svg")
