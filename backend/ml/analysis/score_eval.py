import os, sys
import numpy as np, collections
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupShuffleSplit
X=np.load('ml/analysis/X.npy');y=np.load('ml/analysis/y.npy');g=np.load('ml/analysis/g.npy',allow_pickle=True)
# names order: VL10-100,VL>=100,NNRTI,PI,L2,L3,age<10,age10-19,ART2-5,ART>=5,>=1NS,>=2NS,AZTABC
lowvl=(X[:,0]==0)&(X[:,1]==0)
pts=3*X[:,2]+3*np.maximum(X[:,4],X[:,5])+3*X[:,6]+1*X[:,7]+1*X[:,9]+1*X[:,11]+1*X[:,12]
fit,test=next(GroupShuffleSplit(n_splits=1,test_size=.25,random_state=42).split(X,y,g))
print('AUROC points test',round(roc_auc_score(y[test],pts[test]),3),'all',round(roc_auc_score(y,pts),3))
for s in range(int(pts.max())+1):
    m=pts==s
    if m.sum(): print(s,m.sum(),round(y[m].mean(),2))
for lo,hi in ((0,2),(3,4),(5,99)):
    m=(pts>=lo)&(pts<=hi);print('band',lo,hi,m.sum(),round(m.mean(),2),'rate',round(y[m].mean(),2), 'test rate',round(y[test][(pts[test]>=lo)&(pts[test]<=hi)].mean(),2))
