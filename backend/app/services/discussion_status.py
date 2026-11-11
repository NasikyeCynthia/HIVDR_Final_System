"""Normalize source discussion categories for dashboard and follow-up counts."""

DONE = {'maintained', 'switched', 'substituted'}


def classify_discussion(category=None, decision=None, amplified=None):
    category_text = str(category or '').strip().casefold()
    decision_text = str(decision or '').strip().casefold()
    if category_text in DONE or decision_text in DONE:
        return 'Done'
    if decision_text.startswith(('maintained ', 'switched ', 'substituted ')):
        return 'Done'
    if category_text or decision_text == 'pending':
        return 'Pending'
    try:
        if int(amplified) == 1:
            return 'Pending'
    except (TypeError, ValueError):
        pass
    return ''
