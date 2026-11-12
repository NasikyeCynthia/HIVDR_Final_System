"""Stanford Sierra GraphQL adapter; sends only mutations or a stripped nucleotide sequence."""
import json
import re
import urllib.request
import urllib.error
import math
from datetime import datetime, timezone
from ..core.errors import DomainError

URL = 'https://hivdb.stanford.edu/graphql'
FIELDS = 'validationResults { level message } drugResistance { gene { name } drugScores { drugClass { name } drug { name displayAbbr } score level text } commentsByTypes { commentType comments { text } } }'

LEVELS = {1: 'Susceptible', 2: 'Potential Low-Level Resistance',
          3: 'Low-Level Resistance', 4: 'Intermediate Resistance', 5: 'High-Level Resistance'}


def validate_scores(analysis):
    """Require complete, consistent Sierra results; never invent an absent result."""
    groups = analysis.get('drugResistance')
    if not isinstance(groups, list) or not groups:
        raise DomainError('No interpretable drug-resistance scores were returned. Check sequence coverage or mutation input.', 422)
    for group in groups:
        if not isinstance(group, dict) or not isinstance(group.get('gene'), dict) or group['gene'].get('name') not in ('PR', 'RT', 'IN'):
            raise DomainError('Stanford returned an invalid gene result. No interpretation was created.', 502)
        scores = group.get('drugScores')
        if not isinstance(scores, list) or not scores:
            raise DomainError('Stanford returned an incomplete drug result. No interpretation was created.', 502)
        for item in scores:
            if not isinstance(item, dict):
                raise DomainError('Stanford returned an invalid drug result.', 502)
            score, level = item.get('score'), item.get('level')
            if (type(score) not in (int, float) or not math.isfinite(score)
                    or type(level) is not int or level not in LEVELS
                    or not isinstance(item.get('drug'), dict) or not item['drug'].get('displayAbbr')):
                raise DomainError('Stanford returned an incomplete drug classification. No interpretation was created.', 502)
            expected = 1 if score < 10 else 2 if score < 15 else 3 if score < 30 else 4 if score < 60 else 5
            if level != expected:
                raise DomainError('Stanford score and resistance level disagree. No interpretation was created.', 502)
            # The level is provided by Stanford; labels are normalized for display.
            item['text'] = LEVELS[level]

def status():
    return {'connected': None, 'configured': True, 'message': 'Sierra API configured. Connection is checked when an analysis is requested.'}

def analyze(kind, text):
    if kind not in ('mutations', 'sequence'):
        raise DomainError('Choose mutations or sequence input.')
    if kind == 'mutations':
        tokens = [token for token in re.split(r'[\s,;+]+',text.strip()) if token]
        tokens = list(dict.fromkeys(token.upper() for token in tokens))
        if not tokens or any(not re.fullmatch(r'(PR|RT|IN):[A-Z]?\d+(?:[A-Z*_/\-]+)',token) for token in tokens):
            raise DomainError('Use gene-prefixed mutations, e.g. RT:M184V IN:R263K. Do not include patient identifiers.')
        query = 'query($mutations:[String]!) { currentVersion { text publishDate } mutationsAnalysis(mutations:$mutations) { '+FIELDS+' } }'
        variables = {'mutations': tokens}
        field = 'mutationsAnalysis'
    else:
        # FASTA header is discarded locally; no name or patient ID is transmitted.
        lines = text.splitlines()
        if sum(line.lstrip().startswith('>') for line in lines) > 1:
            raise DomainError('Submit one laboratory sequence at a time; multiple FASTA records cannot be combined.')
        sequence = ''.join(''.join(line.split()) for line in lines if not line.lstrip().startswith('>')).upper()
        if len(sequence)<30 or not re.fullmatch('[ACGTRYSWKMBDHVN]+',sequence):
            raise DomainError('Enter a nucleotide sequence of at least 30 IUPAC bases. FASTA headers are discarded.')
        query = 'query($sequences:[UnalignedSequenceInput]!) { currentVersion { text publishDate } sequenceAnalysis(sequences:$sequences) { '+FIELDS+' } }'
        variables = {'sequences':[{'header':'analysis','sequence':sequence}]}
        field = 'sequenceAnalysis'
    req = urllib.request.Request(URL,data=json.dumps({'query':query,'variables':variables}).encode(),headers={'Content-Type':'application/json','User-Agent':'HIVDR-Surveillance/0.3'})
    try:
        with urllib.request.urlopen(req,timeout=40) as response:
            result = json.load(response)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        raise DomainError('Stanford could not be reached. No interpretation was created; please retry.',502)
    if not isinstance(result, dict):
        raise DomainError('Stanford returned an invalid response. No interpretation was created.',502)
    if result.get('errors'):
        raise DomainError('Stanford rejected the analysis. Check the input and retry; no interpretation was created.',502)
    data = result.get('data') or {}
    if not isinstance(data, dict):
        raise DomainError('Stanford returned invalid analysis data.',502)
    analysis = data.get(field)
    if isinstance(analysis,list): analysis = analysis[0] if analysis else None
    if not isinstance(analysis, dict) or not analysis: raise DomainError('Stanford returned no analysis',502)
    validation = analysis.get('validationResults')
    if not isinstance(validation, list) or any(not isinstance(v, dict) for v in validation):
        raise DomainError('Stanford returned incomplete quality checks.',502)
    severe = [v.get('message','') for v in validation if str(v.get('level','')).upper() in ('ERROR','SEVERE_WARNING','FATAL')]
    if severe:
        raise DomainError('Stanford quality checks require correction: '+'; '.join(severe)[:1000],422)
    validate_scores(analysis)
    if not isinstance(data.get('currentVersion'), dict) or not data['currentVersion'].get('text'):
        raise DomainError('Stanford returned no algorithm version. No interpretation was created.',502)
    return {'version':data['currentVersion'], 'analysis':analysis,'input_kind':kind,
            'provider':'Stanford HIVdb Sierra', 'analyzed_at':datetime.now(timezone.utc).isoformat(),
            'analyzed_genes':[g['gene']['name'] for g in analysis['drugResistance']],
            'submitted_mutations':tokens if kind == 'mutations' else None}
