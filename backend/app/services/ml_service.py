"""Portable JSON inference: no sklearn/joblib runtime or executable model loading."""
import json
import hashlib
import math
import struct
from functools import lru_cache
from pathlib import Path
from .ml_features import extract,transform

ARTIFACTS=Path(__file__).resolve().parents[2]/'ml'/'artifacts'
@lru_cache(maxsize=1)
def model():
    path=ARTIFACTS/'model.json'
    return json.loads(path.read_text()) if path.exists() else None
def sigmoid(x):return 1/(1+math.exp(-max(-700,min(700,x))))
def predict_artifact(artifact,features):
    x=transform(features,artifact['preprocessing'])
    if artifact['kind']=='logistic':
        p=sigmoid(artifact['intercept']+sum(a*b for a,b in zip(x,artifact['coefficients'])))
    else:
        x=[struct.unpack('f',struct.pack('f',v))[0] for v in x]
        values=[]
        for tree in artifact['trees']:
            node=0
            while tree['left'][node]!=-1:
                node=tree['left'][node] if x[tree['feature'][node]]<=tree['threshold'][node] else tree['right'][node]
            values.append(tree['positive_probability'][node])
        p=sum(values)/len(values)
    p=max(1e-6,min(1-1e-6,p));c=artifact['calibration']
    return sigmoid(c['intercept']+c['coefficient']*math.log(p/(1-p)))
def validation_report(artifact):
    """Only expose an aggregate audit matching the exact installed artifact."""
    path=ARTIFACTS/'validation.json'
    try:
        report=json.loads(path.read_text(encoding='utf-8'))
        digest=hashlib.sha256((ARTIFACTS/'model.json').read_bytes()).hexdigest()
        if (report.get('schema_version')==1 and report.get('model_sha256')==digest
                and report.get('data_sha256')==artifact['metadata']['data_sha256']
                and report.get('model_version')==artifact['metadata']['version']):
            return report
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return None

def status():
    artifact=model()
    return {'connected':bool(artifact),'message':'Trained research model available' if artifact else 'No model artifact found',
            'metadata':artifact['metadata'] if artifact else None,
            'validation':validation_report(artifact) if artifact else None}
def predict(raw,patient):
    artifact=model()
    if not artifact:return {'available':False,'reason':'Model artifact missing'}
    features=extract(raw,patient)
    if any(features.get(k) is None for k in ('log_viral_load','treatment_line')):
        return {'available':False,'reason':'Viral load and treatment line are required'}
    if patient.get('source')=='synthetic':return {'available':False,'reason':'Real-outcome model is not scored on synthetic demonstration records'}
    probability=predict_artifact(artifact,features)
    return {'available':True,'probability':probability,'threshold':artifact['metadata']['threshold'],
            'above_research_threshold':probability>=artifact['metadata']['threshold'],
            'version':artifact['metadata']['version'],'model':artifact['metadata']['selected_model'],
            'missing_features':[k for k,v in features.items() if v is None],
            'scope':'Estimated chance of the recorded 12-drug-panel outcome in referred/tested patients; research use only.'}
