#!/usr/bin/env python3
"""
Usage:
  python test_live_site.py          # quick smoke test (5 users)
  python test_live_site.py full     # full 1000-user test
  python test_live_site.py local    # 1000-user test against localhost
"""
import requests
import re
import time
import random
import sys

MODE = (sys.argv[1] if len(sys.argv) > 1 else 'quick').lower()

FIRST_NAMES = [
    'John', 'Maria', 'Michael', 'Sarah', 'David', 'Emma', 'James', 'Olivia',
    'Robert', 'Sophia', 'William', 'Isabella', 'Joseph', 'Mia', 'Thomas',
    'Charlotte', 'Charles', 'Amelia', 'Christopher', 'Harper', 'Daniel',
    'Evelyn', 'Matthew', 'Abigail', 'Anthony', 'Emily', 'Mark', 'Elizabeth',
    'Donald', 'Ava', 'Steven', 'Madison', 'Paul', 'Scarlett', 'Andrew',
    'Victoria', 'Joshua', 'Aria', 'Grace', 'Kevin', 'Chloe',
    'Brian', 'Camila', 'George', 'Penelope', 'Edward', 'Riley', 'Ronald',
    'Layla', 'Timothy', 'Lillian', 'Jason', 'Natalie', 'Jeffrey', 'Nora',
    'Ryan', 'Zoe', 'Jacob', 'Lily', 'Gary', 'Eleanor', 'Nicholas', 'Hannah',
    'Eric', 'Luna', 'Stephen', 'Stella', 'Frank', 'Mila', 'Jonathan', 'Ellie'
]

LAST_NAMES = [
    'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller',
    'Davis', 'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez',
    'Wilson', 'Anderson', 'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin',
    'Lee', 'Perez', 'Thompson', 'White', 'Harris', 'Sanchez', 'Clark',
    'Ramirez', 'Lewis', 'Robinson', 'Walker', 'Young', 'Allen', 'King',
    'Wright', 'Scott', 'Torres', 'Nguyen', 'Hill', 'Flores', 'Green',
    'Adams', 'Nelson', 'Baker', 'Hall', 'Rivera', 'Campbell', 'Mitchell',
    'Carter', 'Roberts', 'Gomez', 'Phillips', 'Evans', 'Turner', 'Diaz',
    'Parker', 'Cruz', 'Edwards', 'Collins', 'Reyes', 'Stewart', 'Morris',
    'Morales', 'Murphy', 'Cook', 'Rogers', 'Gutierrez', 'Ortiz', 'Morgan',
    'Cooper', 'Peterson', 'Bailey', 'Reed', 'Kelly', 'Howard', 'Ramos'
]

if MODE == 'local':
    BASE_URL = 'http://127.0.0.1:5000'
    SECONDS_BETWEEN = 0.01
else:
    BASE_URL = 'https://nlcfregform.pythonanywhere.com'
    SECONDS_BETWEEN = 0.5

TOTAL = 1000 if MODE in ('full', 'local') else 5

def get_churches(html):
    matches = re.findall(r'<option value="(\d+)">([^<]+)</option>', html)
    return [(int(id), name) for id, name in matches if id.isdigit()]

def register_user(session, churches):
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    gender = random.choice(['Male', 'Female'])
    age = random.randint(1, 80)
    church_id, _ = random.choice(churches)

    data = {
        'first_name': first,
        'last_name': last,
        'gender': gender,
        'age': str(age),
        'church_id': str(church_id),
    }

    try:
        resp = session.post(BASE_URL + '/register', data=data, allow_redirects=True, timeout=15)
        if 'REG-' in resp.text:
            m = re.search(r'REG-\d{4}', resp.text)
            code = m.group(0) if m else '?'
            return True, (first, last, age, gender, code)
        else:
            return False, (f'HTTP_{resp.status_code}',)
    except Exception as e:
        return False, (f'ERROR: {e}',)

def main():
    print(f'Mode: {MODE} | {BASE_URL} | Target: {TOTAL} users')

    session = requests.Session()
    r = session.get(BASE_URL + '/register', timeout=15)
    if r.status_code != 200:
        print(f'FAILED: HTTP {r.status_code}'); return

    churches = get_churches(r.text)
    print(f'Churches: {len(churches)}\n')

    success = 0
    failed = 0
    start = time.time()

    for i in range(1, TOTAL + 1):
        ok, info = register_user(session, churches)
        if ok:
            success += 1
        else:
            failed += 1

        if i % 100 == 0 or MODE == 'quick':
            elapsed = time.time() - start
            if ok:
                print(f'[{i:>4}] {info[0]} {info[1]} (Age {info[2]}, {info[3]}) - {info[4]}')
            else:
                print(f'[{i:>4}] {info[0]}')

        if SECONDS_BETWEEN > 0:
            time.sleep(SECONDS_BETWEEN)

    elapsed = time.time() - start
    print(f'\n{"=" * 50}')
    print(f'  SUCCESS: {success}/{TOTAL}')
    print(f'  FAILED:  {failed}')
    print(f'  TIME:    {elapsed:.1f}s ({elapsed/60:.1f}min)')
    if elapsed > 0:
        print(f'  RATE:    {success/(elapsed/60):.1f}/min')
    print(f'{"=" * 50}')

if __name__ == '__main__':
    main()
