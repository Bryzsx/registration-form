#!/usr/bin/env python3
"""
Test script to register 1000 users with random data on the live site.
Run with: python test_live_site.py
"""
import requests
from datetime import datetime, timedelta
import time
import random
import re

BASE_URL = 'https://nlcfregform.pythonanywhere.com'

# Dummy data for realistic testing
FIRST_NAMES = [
    'John', 'Maria', 'Michael', 'Sarah', 'David', 'Emma', 'James', 'Olivia',
    'Robert', 'Sophia', 'William', 'Isabella', 'Joseph', 'Mia', 'Thomas',
    'Charlotte', 'Charles', 'Amelia', 'Christopher', 'Harper', 'Daniel',
    'Evelyn', 'Matthew', 'Abigail', 'Anthony', 'Emily', 'Mark', 'Elizabeth',
    'Donald', 'Ava', 'Steven', 'Madison', 'Paul', 'Scarlett', 'Andrew',
    'Victoria', 'Joshua', 'Aria', 'Kenneth', 'Grace', 'Kevin', 'Chloe',
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

MIDDLE_NAMES = ['', 'James', 'Marie', 'Lee', 'Ann', 'Ray', 'Louise', 'Joe', 'Mary', 'John', 'Patricia', 'Michael']

def get_churches(session):
    """Get list of available churches from the register page"""
    try:
        response = session.get(BASE_URL + '/register', timeout=10)
        churches = re.findall(r'<option value="(\d+)">([^<]+)</option>', response.text)
        if churches:
            return [(int(id), name) for id, name in churches if id.isdigit()]
    except Exception as e:
        print('  Error getting churches: ' + str(e))
    return [(1, 'Default Church')]

def generate_birth_date():
    """Generate a random birth date for ages 1-80"""
    age = random.randint(1, 80)
    birth_date = datetime.now() - timedelta(days=365*age + random.randint(0, 364))
    return birth_date.strftime('%Y-%m-%d'), age

def register_user(session, index, churches):
    """Register a single user with random data"""
    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)
    gender = random.choice(['Male', 'Female'])
    age = random.randint(1, 80)
    
    church_id, church_name = random.choice(churches)
    
    data = {
        'first_name': first_name,
        'last_name': last_name,
        'gender': gender,
        'age': str(age),
        'church_id': str(church_id)
    }
    
    try:
        response = session.post(BASE_URL + '/register', data=data, allow_redirects=True, timeout=10)
        if 'REG-' in response.text:
            match = re.search(r'REG-\d{4}', response.text)
            if match:
                if index % 100 == 0:
                    msg = '  User ' + str(index) + ': ' + first_name + ' ' + last_name
                    msg += ' (Age ' + str(age) + ', ' + gender + ') - ' + match.group(0)
                    print(msg)
            else:
                print('  User ' + str(index) + ': Registered but code not found')
            return True
        else:
            print('  User ' + str(index) + ': Failed - Status ' + str(response.status_code))
            return False
    except Exception as e:
        print('  User ' + str(index) + ': Error - ' + str(e))
        return False

def main():
    print('=' * 70)
    print('Testing 1000 registrations with RANDOM data on live site')
    print('Site: ' + BASE_URL)
    print('Features: Random names, ages (1-80), genders, churches')
    print('=' * 70)
    
    session = requests.Session()
    
    print('\nFetching available churches...')
    churches = get_churches(session)
    church_names = [name for _, name in churches[:3]]
    print('Found ' + str(len(churches)) + ' churches: ' + str(church_names) + '...')
    
    success_count = 0
    failed_count = 0
    
    start_time = time.time()
    
    print('\nStarting registration process...\n')
    
    for i in range(1, 1001):
        if i % 100 == 0:
            elapsed = time.time() - start_time
            msg = '\nProgress: ' + str(i) + '/1000 (10%) - Elapsed: '
            msg += str(round(elapsed, 1)) + 's - Success: ' + str(success_count) + '\n'
            print(msg)
        
        if register_user(session, i, churches):
            success_count += 1
        else:
            failed_count += 1
        
        if i % 10 != 0:
            time.sleep(0.8)
        else:
            time.sleep(1.5)
    
    elapsed = time.time() - start_time
    print('\n' + '=' * 70)
    msg = 'FINAL RESULTS: ' + str(success_count) + '/1000 successful, '
    msg += str(failed_count) + ' failed'
    print(msg)
    msg = 'Total time: ' + str(round(elapsed, 1)) + ' seconds ('
    msg += str(round(elapsed/60, 1)) + ' minutes)'
    print(msg)
    print('=' * 70)

if __name__ == '__main__':
    main()
