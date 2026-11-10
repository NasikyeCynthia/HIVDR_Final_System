"""Prepare gene-qualified tokens from recorded genotype columns, never from patient text."""
import re

def suggested_mutations(raw):
    groups={'PR':['PI','PiMajor Mutations','PiMinor Mutations','PI Mutations Combined'],
            'RT':['NRTI','NNRTI','NRTI Mutations','NNRTI Mutations'],
            'IN':['INSTI','INSTI Mutations']}
    tokens=[]
    for gene,columns in groups.items():
        for column in columns:
            for mutation in re.findall(r'\b([A-Z]\d+[A-Z*/]+)',str(raw.get(column) or '')):
                token=gene+':'+mutation
                if token not in tokens:tokens.append(token)
    return ' '.join(tokens)

def has_genotype(raw):
    return bool(suggested_mutations(raw) or re.search(r'\b[A-Z]\d+[A-Z*/]+',str(raw.get('All Mutations Combined') or '')))
