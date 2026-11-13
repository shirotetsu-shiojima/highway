import math, json, numpy as np
K=180/math.pi
def Y(lat): return math.log(math.tan(math.pi/4+math.radians(lat)/2))
# (name, Gx, Gz, lon, lat)  実在座標は記憶ベースの概算(±0.02°程度)。後で OSM データで精密化する前提の暫定値。
ANCH=[('吹田JCT',9011.03,5049.93,135.5317,34.8094),('三郷JCT',10818.37,5575.63,139.8628,35.8150),
      ('大泉JCT',10709.64,5535.6,139.5867,35.7586),('鶴ヶ島JCT',10629.08,5625.93,139.3969,35.9325),
      ('海ほたるPA',10826.75,5386.18,139.8730,35.4640),('セントレア',9541.26,4913.42,136.8054,34.8584)]
def fit(anch=ANCH):
    A=[];b=[]
    for n,gx,gz,lon,lat in anch:
        A.append([lon,1,0]);b.append(gx)
        A.append([K*Y(lat),0,1]);b.append(gz)
    sol,res,_,_=np.linalg.lstsq(np.array(A),np.array(b),rcond=None)
    return sol
def make(sol):
    s,a,b=sol
    def to_ll(gx,gz):
        lon=(gx-a)/s; y=(gz-b)/(s*K)
        return lon, math.degrees(2*math.atan(math.exp(y))-math.pi/2)
    return to_ll
if __name__=='__main__':
    sol=fit(); print('scale',sol)
    f=make(sol)
    for n,gx,gz,lon,lat in ANCH:
        l,t=f(gx,gz); print(n,'dlon',round((l-lon)*sol[0],1),'dlat(units)',round((t-lat)*sol[0]/math.cos(math.radians(lat)),1))
    for n,gx,gz in [('Tokyo',10790,5500),('Fukuoka',7050,4570),('鳥栖JCT',6912.21,4337.85),('那須高原SA',10920,6209),('諏訪湖SA',10071,5675),('宝塚北SA',8910,5080)]:
        print(n,[round(v,3) for v in f(gx,gz)])
