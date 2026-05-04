import os

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace curly quotes with straight quotes
    content = content.replace(''', '"').replace(''', '"')
    content = content.replace(''', '(').replace(''', ')')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'Fixed: {filepath}')

# Fix template files
fix_file('templates/admin.html')
fix_file('templates/register.html')
fix_file('templates/login.html')
fix_file('templates/index.html')
fix_file('templates/success.html')
fix_file('templates/base.html')

# Fix CSS file
fix_file('static/css/style.css')

print('All files fixed!')
