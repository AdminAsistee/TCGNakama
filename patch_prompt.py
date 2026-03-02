em_dash = '\u2014'
path = r'app/services/appraisal.py'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find and replace the CRITICAL OVERRIDE line
for i, line in enumerate(lines):
    if 'CRITICAL OVERRIDE' in line and 'COLORED BOX' in line:
        # Replace with expanded version
        indent = '     '
        lines[i] = (
            f'{indent}* CRITICAL OVERRIDE \u2014 Pok\u00e9mon TCG Classic set (CLL): Some Japanese cards that look like '
            f'vintage Base Set/Team Rocket Trainer cards were reprinted in 2023 as "Pok\u00e9mon Card Game Classic". '
            f'These have a small RED RECTANGULAR BOX at the BOTTOM LEFT corner (NOT a circle regulation mark) '
            f'containing the letters "CLL". Next to that box is the card number in ###/### format (e.g. 027/032). '
            f'LOOK CAREFULLY at the bottom-left area of the card. If you see a colored rectangle with letters '
            f'before a ###/### number: that rectangle IS the set code (set_name = "CLL"), and only the ###/### '
            f'part is the card_number. full_set_name = "Pok\u00e9mon Card Game Classic". '
            f'These cards also have copyright text starting with "\u00a92023 Pok\u00e9mon" near the bottom.\n'
        )
        print(f'Updated CRITICAL OVERRIDE at line {i + 1}')
        break
else:
    print('CRITICAL OVERRIDE line not found')

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Done')
