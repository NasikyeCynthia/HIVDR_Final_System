"""Psychosocial barriers → recommended support, from the MoH psychosocial support (PSS)
service packages (Desktop Job Aid 2020, slides 41–49 and 65–69) and the PSS fields of the
CPHL HIVDR database. Recommendations support the counsellor; they are not risk points."""

FACTORS = {
    'Non-disclosure': 'Disclosure counselling (age-appropriate for children); support disclosure to a treatment supporter or partner.',
    'Denial/coping with results': 'Counselling on acceptance of HIV status and of the non-suppressed result; coping and emotional support; link to an expert client.',
    'Anger/Stress': 'Coping and emotional support; screen for depression with the two-question tool and refer for mental-health review if both are “yes”.',
    'Stigma & discrimination': 'Address self-stigma; link to peer support groups; legal or social support where discrimination occurs.',
    'Bereavement': 'Bereavement counselling (play therapy for children under 10); check who now supervises doses.',
    'Dysfunctional family/client support system': 'Family counselling with the social worker; identify a treatment supporter; OVC assessment for children.',
    'Harmful habits (Alcohol & substance abuse)': 'Alcohol/substance-use risk-reduction counselling and referral; plan dosing around drinking patterns.',
    'Risky sexual behaviours': 'HIV risk-reduction counselling (partner reduction, condoms, partner testing); screen for GBV.',
    'Lack of life-survival skills': 'Life-skills education (self-awareness, decision making); adolescent peer groups.',
    'Transition challenges': 'Adolescent transition support: adolescent-friendly clinic, peer group, transition plan with caregiver.',
    'Economic challenges/poverty': 'Referral to livelihood and socio-economic support; consider a differentiated service model to reduce travel costs.',
    'Had 1 or no meal/day': 'Nutrition assessment and food support; time doses with available meals.',
    'Malnourished': 'Nutrition assessment and therapeutic/supplementary feeding; review dosing by weight for children.',
    'Spiritual issues (Religious beliefs, Drug holidays etc)': 'Counsel on drug holidays and faith-based beliefs; engage spiritual leaders where acceptable.',
    'Fear/Anxiety': 'Coping and emotional support; screen for depression and anxiety; refer for mental-health review if indicated.',
}
DEFAULT_ACTION = 'Address the barrier in the next IAC session and record an agreed action (5 As: assess, advise, agree, assist, arrange).'


def recommendations(psychosocial, age=None):
    factors = (psychosocial or {}).get('factors') or []
    result = [{'factor': f, 'action': FACTORS.get(f, DEFAULT_ACTION)} for f in factors]
    if not (psychosocial or {}).get('assessed'):
        result.insert(0, {'factor': 'Assessment not done', 'action': 'Complete the psychosocial assessment before the committee review.'})
    if age is not None and 10 <= age < 20:
        result.append({'factor': 'Adolescent (10–19 years)', 'action': 'Use the HEADSS assessment; offer adolescent-friendly services and peer support.'})
    if age is not None and age < 10:
        result.append({'factor': 'Child under 10', 'action': 'Assess the caregiver’s adherence support and treatment knowledge; age-appropriate disclosure plan.'})
    return result
