"""Stanford Sierra GraphQL adapter; sends only mutations or a stripped nucleotide sequence."""
import json
import re
import urllib.request
import urllib.error
from ..core.errors import DomainError

URL = 'https://hivdb.stanford.edu/graphql'
FIELDS = 'validationResults { level message } drugResistance { gene { name } drugScores { drugClass { name } drug { name displayAbbr } score level text } commentsByTypes { commentType comments { text } } }'

def status():
    return {'connected': None, 'configured': True, 'message': 'Sierra API configured. Connection is checked when an analysis is requested.'}

def analyze(kind, text):
    if kind == 'mutations':
        tokens = [token for token in re.split(r'[\s,;+]+',text.strip()) if token]
        if not tokens or any(not re.fullmatch(r'(PR|RT|IN):[A-Za-z0-9_*/.\-]+',token) for token in tokens):
            raise DomainError('Use gene-prefixed mutations, e.g. RT:M184V IN:R263K. Do not include patient identifiers.')
        query = 'query($mutations:[String]!) { currentVersion { text publishDate } mutationsAnalysis(mutations:$mutations) { '+FIELDS+' } }'
        variables = {'mutations': tokens}
        field = 'mutationsAnalysis'
    else:
        # FASTA header is discarded locally; no name or patient ID is transmitted.
        sequence = ''.join(line.strip() for line in text.splitlines() if not line.startswith('>')).replace(' ','').upper()
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
    if result.get('errors'):
        raise DomainError('Stanford rejected the analysis: '+'; '.join(e.get('message','Query error') for e in result['errors'])[:1000],502)
    data = result.get('data') or {}
    analysis = data.get(field)
    if isinstance(analysis,list): analysis = analysis[0] if analysis else None
    if not analysis: raise DomainError('Stanford returned no analysis',502)
    severe = [v.get('message','') for v in analysis.get('validationResults',[]) if str(v.get('level','')).upper() in ('ERROR','SEVERE_WARNING','FATAL')]
    if severe:
        raise DomainError('Stanford quality checks require correction: '+'; '.join(severe)[:1000],422)
    if not any(g.get('drugScores') for g in analysis.get('drugResistance',[])):
        raise DomainError('No interpretable drug-resistance scores were returned. Check sequence coverage or mutation input.',422)
    return {'version':data.get('currentVersion'), 'analysis':analysis,'input_kind':kind,'provider':'Stanford HIVdb Sierra'}
