"""Prepare gene-qualified tokens from recorded genotype columns, never from patient text."""
import re

GROUPS={'PI':('PR',['PI','PiMajor Mutations','PiMinor Mutations','PI Mutations Combined']),
        'INSTI':('IN',['INSTI','INSTI Mutations']),
        'NRTI':('RT',['NRTI','NRTI Mutations']),
        'NNRTI':('RT',['NNRTI','NNRTI Mutations'])}


def validate_group_input(text, gene):
    """Accept laboratory frequencies, but require every remaining token to be a mutation."""
    cleaned=re.sub(r'\(\s*\d+(?:\.\d+)?\s*%\s*\)', '', str(text or '').upper())
    tokens=[t for t in re.split(r'[\s,;+]+',cleaned) if t]
    if not tokens:
        return []
    result=[]
    for token in tokens:
        if ':' in token:
            prefix,token=token.split(':',1)
            if prefix!=gene: raise ValueError('Mutation gene does not match this field: '+prefix)
        if not re.fullmatch(r'[A-Z]?\d+[A-Z*_/\-]+',token):
            raise ValueError('Unrecognised mutation: '+token+'. Enter e.g. M184V or M184V(99.2%).')
        qualified=gene+':'+token
        if qualified not in result:result.append(qualified)
    return result

def suggested_mutations(raw):
    tokens=[]
    # Preserve the existing gene order for saved report compatibility.
    groups={'PR':GROUPS['PI'][1], 'RT':GROUPS['NRTI'][1]+GROUPS['NNRTI'][1], 'IN':GROUPS['INSTI'][1]}
    for gene,columns in groups.items():
        for column in columns:
            for mutation in re.findall(r'\b([A-Z]?\d+[A-Z*_/\-]+)',str(raw.get(column) or '').upper()):
                token=gene+':'+mutation
                if token not in tokens:tokens.append(token)
    for token in re.findall(r'\b(?:PR|RT|IN):[A-Z]?\d+[A-Z*_/\-]+',str(raw.get('All Mutations Combined') or '').upper()):
        if token not in tokens:tokens.append(token)
    return ' '.join(tokens)


def analysis_input(raw, episode_mutations=''):
    """Use gene-specific report evidence ahead of an unqualified combined column."""
    qualified=re.findall(r'\b(?:PR|RT|IN):[A-Z]?\d+[A-Z*_/\-]+',str(episode_mutations or '').upper())
    if qualified and all(re.fullmatch(r'(?:PR|RT|IN):[A-Z]?\d+[A-Z*_/\-]+',t) for t in re.split(r'[\s,;+]+',str(episode_mutations).upper()) if t):
        return ' '.join(dict.fromkeys(qualified))
    return suggested_mutations(raw)

def has_genotype(raw):
    return bool(suggested_mutations(raw) or re.search(r'\b[A-Z]\d+[A-Z*/]+',str(raw.get('All Mutations Combined') or '')))
