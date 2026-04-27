import re

def parse_player_input(raw_text: str) -> tuple:
    text = raw_text.lower().strip()
    if text in ('yes','yeah','sure','ok','deal','accept','y','go ahead'):
        return ('CONFIRM', {})
    if text in ('no','cancel','nevermind','stop'):
        return ('CANCEL', {})
    if text.isdigit():
        return ('NUMBER', {'value': int(text)})
    match = re.search(r'\b(\d+)\b', text)
    if match:
        return ('NUMBER', {'value': int(match.group(1))})
    if text in ('fight','attack','kill','engage'):
        return ('FIGHT', {})
    if text in ('flee','run','escape','retreat'):
        return ('FLEE', {})
    if text in ('parley','talk','bribe','negotiate'):
        return ('PARLEY', {})
    return ('RAW', {'text': text})