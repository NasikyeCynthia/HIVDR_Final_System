"""Decision support for the switch committee: Maintain, Substitute or Switch.

Stanford HIVdb reports drug-level resistance only; it does not recommend a regimen action
(MoH Participants' Manual §5.3: the report "does not have the logical power to instruct
clinicians on which ARVs should be used"). This module turns the Stanford levels for the
patient's CURRENT regimen into a suggested action using WHO 2021 and MoH guidance. The
clinician must approve or change it; the suggestion and whether it was followed are audited.

Agreement with past Ugandan committee decisions is reported in RISK_SCORE.md.
"""
import json
from .eligibility_service import regimen_drugs

VERSION = 'decision-support-2026.1'
LEVEL = {'Susceptible': 1, 'Potential Low-Level Resistance': 2, 'Low-Level Resistance': 3,
         'Intermediate Resistance': 4, 'High-Level Resistance': 5}
NAMES = {1: 'Susceptible', 2: 'Potential low-level', 3: 'Low-level', 4: 'Intermediate', 5: 'High-level'}
ALIAS = {'LPV': 'LPV/r', 'ATV': 'ATV/r', 'DRV': 'DRV/r', 'ZDV': 'AZT', 'FTC': '3TC', 'RTV': None}
INSTI, PI, NNRTI, NRTI = {'DTG', 'RAL', 'BIC', 'CAB', 'EVG'}, {'LPV/r', 'ATV/r', 'DRV/r'}, {'EFV', 'NVP', 'ETR', 'RPV', 'DOR'}, {'TDF', '3TC', 'ABC', 'AZT', 'TAF'}
ALL_DRUGS = ['DTG', 'BIC', 'CAB', 'RAL', 'DRV/r', 'LPV/r', 'ATV/r', 'TDF', '3TC', 'ABC', 'AZT', 'EFV', 'NVP', 'ETR', 'DOR']
SOURCES = {
    'WHO-2021': 'WHO consolidated guidelines 2021 — management of treatment failure',
    'MOH-161': 'MoH Desktop Job Aid 2020, slides 161–162 — second- and third-line ART; third line guided by resistance testing',
    'MANUAL-5.3': 'MoH HIVDR Participants’ Manual §5.3 — interpreting Stanford levels',
    'COMMITTEE': 'Pattern of past Ugandan switch-committee decisions in the CPHL extract',
}


def drug_levels(e, raw):
    """Stanford levels per drug: saved Stanford analysis first, else the recorded dataset results."""
    levels, source = {}, None
    interp = json.loads(e.get('interpretation_json') or 'null') if isinstance(e.get('interpretation_json'), str) else e.get('interpretation')
    for gene in ((interp or {}).get('analysis') or {}).get('drugResistance', []) or []:
        for d in gene.get('drugScores', []):
            abbr = (d.get('drug') or {}).get('displayAbbr', '')
            name = ALIAS.get(abbr.split('/')[0], abbr) if abbr not in ('LPV/r', 'ATV/r', 'DRV/r') else abbr
            if name and d.get('level'):
                levels[name] = int(d['level'])
                source = 'Stanford HIVdb ' + str(((interp or {}).get('version') or {}).get('text', ''))
    if not levels:
        for drug in ALL_DRUGS:
            value = raw.get('Resistance to ' + drug)
            if value in LEVEL:
                levels[drug] = LEVEL[value]
        source = 'Recorded laboratory report' if levels else None
    return levels, source


def suggest(patient, e, raw):
    if e.get('status') != 'Usable result':
        return None
    levels, source = drug_levels(e, raw)
    regimen = patient.get('regimen') or raw.get('ART at sample collection(ART@VL@DR)') or ''
    drugs = [ALIAS.get(d, d) for d in regimen_drugs(regimen)]
    drugs = [d for d in drugs if d]
    current = [{'drug': d, 'level': levels.get(d), 'label': NAMES.get(levels.get(d), 'Not reported')} for d in drugs]
    active = [d for d in ALL_DRUGS if levels.get(d) is not None and levels[d] <= 2]
    base = {'version': VERSION, 'regimen': regimen, 'current_regimen': current, 'evidence_source': source,
            'fully_active_drugs': active, 'sources': SOURCES,
            'notice': 'Suggestion only. The clinician approves or changes it after reviewing history, adherence and psychosocial factors.'}
    if not levels:
        return {**base, 'action': None, 'rationale': ['No drug-level resistance results are recorded yet. Run the Stanford interpretation first.']}
    anchors = [d for d in drugs if d in INSTI | PI | NNRTI]
    nrtis = [d for d in drugs if d in NRTI]
    if not anchors or any(levels.get(d) is None for d in anchors):
        return {**base, 'action': None, 'rationale': ['The anchor drug of the current regimen could not be matched to a resistance result; review manually.']}
    anchor = anchors[0]
    a = levels[anchor]
    compromised = [d for d in nrtis if (levels.get(d) or 0) >= 4]
    why, action, alternative = [], None, None
    cls = 'NNRTI' if anchor in NNRTI else 'PI' if anchor in PI else 'INSTI'
    if cls == 'NNRTI' and a >= 3:
        action = 'Switched'
        why.append(f'{anchor} has {NAMES[a].lower()} resistance; NNRTIs have a low genetic barrier, so WHO advises switching to a DTG-based regimen.')
    elif a >= 4:
        action = 'Switched'
        why.append(f'The anchor drug {anchor} has {NAMES[a].lower()} resistance, so the current regimen is compromised.')
        if cls == 'INSTI':
            why.append('Third-line regimens are chosen from the full resistance profile (MoH); typically a boosted PI with the most active NRTIs.')
    elif a == 3:
        if len(compromised) >= 2:
            action = 'Switched'
            why.append(f'{anchor} has low-level resistance and the NRTI backbone ({", ".join(compromised)}) is compromised.')
        else:
            action, alternative = 'Maintained', 'Switched'
            why.append(f'{anchor} has only low-level resistance and the backbone is largely active; maintain with close VL follow-up, or switch if the committee judges the risk too high.')
    else:
        if nrtis and len(compromised) >= len(nrtis) and len(nrtis) >= 2:
            action, alternative = 'Switched', 'Substituted'
            why.append(f'{anchor} is active but both NRTIs ({", ".join(compromised)}) have intermediate or high-level resistance, leaving a functional monotherapy.')
        elif compromised:
            action, alternative = 'Maintained', 'Substituted'
            why.append(f'{anchor} is fully active and has a high genetic barrier; {", ".join(compromised)} is compromised. '
                       'Maintaining is usual practice; substituting the compromised NRTI is an alternative.')
        else:
            action = 'Maintained'
            why.append('No meaningful resistance to the current regimen: the non-suppression is most likely due to adherence. '
                       'Continue the regimen with intensified adherence and psychosocial support.')
    if cls == 'NNRTI' and action == 'Maintained':
        why.append('Note: Uganda has transitioned most patients from NNRTI- to DTG-based regimens; consider a programmatic transition.')
    return {**base, 'action': action, 'alternative': alternative, 'anchor': anchor, 'anchor_class': cls,
            'compromised_nrtis': compromised, 'rationale': why}
