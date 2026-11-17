"""Versioned, portable research-model inference; no sklearn runtime dependency."""
import hashlib
import json
import math
import struct
from functools import lru_cache
from pathlib import Path
from .ml_features import extract, transform

ARTIFACTS = Path(__file__).resolve().parents[2] / 'ml' / 'artifacts'

def selection():
    path = ARTIFACTS / 'active_model.json'
    if not path.exists():
        return {'key': 'v1', 'path': ARTIFACTS / 'model.json'}
    manifest = json.loads(path.read_text(encoding='utf-8'))
    paths = {'v1': ARTIFACTS / 'model.json',
             'history-v2': ARTIFACTS.parent / 'experiments' / 'history-v2' / 'model.json'}
    if manifest.get('model') not in paths:
        raise ValueError('Unknown active research model. Check ml/artifacts/active_model.json.')
    return {**manifest, 'key': manifest['model'], 'path': paths[manifest['model']]}

@lru_cache(maxsize=1)
def model():
    selected = selection()
    path = selected['path']
    if not path.exists():
        if selected['key'] == 'v1': return None
        raise ValueError('The configured retrained model artifact is missing.')
    data = path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if selected.get('sha256') and selected['sha256'] != digest:
        raise ValueError('Active model fingerprint mismatch; no predictions were created.')
    artifact = json.loads(data)
    schema = 'history-v2' if selected['key'] == 'history-v2' else 'original-v1'
    artifact['_runtime'] = {'feature_schema': schema, 'sha256': digest, 'key': selected['key'],
                            'pipeline_version': schema+'-runtime-1'}
    metadata = artifact['metadata']
    if schema == 'history-v2':
        if metadata.get('feature_set') != 'history' or artifact['kind'] != 'forest':
            raise ValueError('The selected artifact does not match the history-v2 extractor.')
        from .ml_history_features import NUMERIC, CATEGORICAL
        if list(artifact['preprocessing']['numeric']) != NUMERIC or list(artifact['preprocessing']['categorical']) != CATEGORICAL:
            raise ValueError('Retrained model feature order does not match the runtime extractor.')
        metadata = {**metadata, 'training_artifact_version': metadata['version'],
                    'version': 'hivdr-panel-v2-history', 'status': 'active_research',
                    'held_out_test': metadata['legacy_test'],
                    'evaluation_label': 'Previously examined legacy-test comparison',
                    'feature_schema': schema}
        artifact['metadata'] = metadata
    return artifact

def sigmoid(x):
    return 1 / (1 + math.exp(-max(-700, min(700, x))))

def predict_artifact(artifact, features):
    x = transform(features, artifact['preprocessing'])
    if artifact['kind'] == 'logistic':
        p = sigmoid(artifact['intercept'] + sum(a*b for a,b in zip(x, artifact['coefficients'])))
    elif artifact['kind'] == 'forest':
        # sklearn trees use float32 features against double-precision thresholds.
        x = [struct.unpack('f', struct.pack('f', v))[0] for v in x]
        values = []
        for tree in artifact['trees']:
            node = 0
            while tree['left'][node] != -1:
                node = tree['left'][node] if x[tree['feature'][node]] <= tree['threshold'][node] else tree['right'][node]
            values.append(tree['positive_probability'][node])
        p = sum(values) / len(values)
    else:
        raise ValueError('Unsupported portable model kind.')
    p = max(1e-6, min(1-1e-6, p))
    c = artifact['calibration']
    return sigmoid(c['intercept'] + c['coefficient'] * math.log(p/(1-p)))

def validation_report(artifact):
    """Do not attach the old model's audit to a different active model."""
    if artifact.get('_runtime', {}).get('feature_schema') == 'history-v2': return None
    path = ARTIFACTS / 'validation.json'
    try:
        report = json.loads(path.read_text(encoding='utf-8'))
        digest = hashlib.sha256((ARTIFACTS/'model.json').read_bytes()).hexdigest()
        if (report.get('schema_version') == 1 and report.get('model_sha256') == digest
                and report.get('data_sha256') == artifact['metadata']['data_sha256']
                and report.get('model_version') == artifact['metadata']['version']):
            return report
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return None

@lru_cache(maxsize=1)
def retraining_report():
    selected = selection()
    if selected['key'] != 'history-v2': return None
    data = selected['path'].with_name('metrics.json').read_bytes()
    if hashlib.sha256(data).hexdigest() != selected.get('metrics_sha256'):
        raise ValueError('Retraining report fingerprint mismatch.')
    return json.loads(data)

def status():
    artifact = model()
    report = retraining_report() if artifact else None
    metadata = dict(artifact['metadata']) if artifact else None
    if metadata is not None and report:
        metadata['development_comparison'] = report['development_comparison']
    return {'connected': bool(artifact),
            'message': 'Trained research model available' if artifact else 'No model artifact found',
            'metadata': metadata, 'validation': validation_report(artifact) if artifact else None,
            'retraining_evaluation': report}

def predict(raw, patient):
    artifact = model()
    if not artifact: return {'available': False, 'reason': 'Model artifact missing'}
    runtime = artifact['_runtime'];meta = artifact['metadata']
    stamp = {'version': meta['version'], 'model': meta['selected_model'],
             'model_sha256': runtime['sha256'], 'feature_schema': runtime['feature_schema'],
             'pipeline_version': runtime['pipeline_version']}
    if patient.get('source') == 'synthetic' or patient.get('dataset_source') == 'synthetic':
        return {**stamp, 'available': False, 'reason': 'Real-outcome model is not scored on synthetic demonstration records'}
    if runtime['feature_schema'] == 'history-v2':
        from .ml_history_features import extract as extract_features
    else:
        extract_features = extract
    features = extract_features(raw, patient)
    if any(features.get(k) is None for k in ('log_viral_load', 'treatment_line')):
        return {**stamp, 'available': False, 'reason': 'Viral load and treatment line are required'}
    probability = predict_artifact(artifact, features)
    return {**stamp, 'available': True, 'probability': probability, 'threshold': meta['threshold'],
            'above_research_threshold': probability >= meta['threshold'],
            'missing_features': [k for k,v in features.items() if v is None],
            'reference_sample_date': raw.get('Sample collection Date') or None,
            'scope': 'Estimated chance of the recorded 12-drug-panel outcome in referred/tested patients; research use only.'}

def refresh_cached_predictions(batch_size=100):
    """Refresh only ML cache fields; never change clinical data or decisions.

    Read/compute/write in short batches. Compare source and risk snapshot versions
    before updating so concurrent clinical edits cannot be replaced by stale inputs.
    """
    from ..core.database import connect
    artifact = model()
    if not artifact: return {'updated': 0, 'skipped': 0}
    digest = artifact['_runtime']['sha256'];pipeline = artifact['_runtime']['pipeline_version']
    last_id = 0;updated = 0;skipped = 0
    while True:
        with connect() as con:
            rows = con.execute("""SELECT p.id,p.data_version,p.source,p.dataset_source,p.age,p.sex,p.regimen,
                p.treatment_line,p.viral_load,p.original_json,p.source_overrides_json,e.risk_json
                FROM patients p JOIN episodes e ON e.patient_id=p.id
                WHERE p.id>? AND (COALESCE(json_extract(e.risk_json,'$.ml.model_sha256'),'')!=?
                OR COALESCE(json_extract(e.risk_json,'$.ml.pipeline_version'),'')!=?)
                ORDER BY p.id LIMIT ?""", (last_id, digest, pipeline, batch_size)).fetchall()
        if not rows: break
        updates = []
        for row in rows:
            p = dict(row);last_id = p['id']
            raw = {**json.loads(p.get('original_json') or '{}'), **json.loads(p.get('source_overrides_json') or '{}')}
            ml = predict(raw, p)
            risk = json.loads(p['risk_json'] or '{}');risk['ml'] = ml
            updates.append((json.dumps(risk),round(ml['probability'],3) if ml.get('available') else None,
                            p['id'],p['risk_json'],p['id'],p['data_version']))
        with connect() as con:
            for values in updates:
                changed = con.execute("""UPDATE episodes SET risk_json=?,risk_ml=?
                    WHERE patient_id=? AND risk_json IS ?
                    AND EXISTS(SELECT 1 FROM patients WHERE id=? AND data_version=?)""", values).rowcount
                updated += changed;skipped += 1-changed
    return {'updated': updated, 'skipped': skipped, 'version': artifact['metadata']['version']}
