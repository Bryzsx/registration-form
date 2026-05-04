import re

with open('app.py', 'r') as f:
    content = f.read()

# Fix column definitions - add missing parentheses
# Pattern: db.Column(type), constraint) -> db.Column(type, constraint)
content = re.sub(r'db\.Column\((db\.\w+\.\w+),\s*(nullable)', r'db.Column(\1, \2)', content)
content = re.sub(r'db\.Column\((db\.\w+),\s*(primary_key)', r'db.Column(\1, \2)', content)
content = re.sub(r'db\.Column\(db\.String\(\d+\)\),\s*(unique|nullable)', r'db.Column(db.String(\1), \2)', content)

# Fix f-strings with curly braces
content = content.replace('f"REG-{new_num:04d}"', "f'REG-{new_num:04d}'")
content = content.replace('f\'registrations_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx\'', "f'registrations_{datetime.now().strftime(\"%Y%m%d_%H%M%S\")}.xlsx'")

# Fix method decorators
content = content.replace("@app.route('/admin/church/<int:id>/delete')", "@app.route('/admin/church/<int:id>/delete')")
content = content.replace("@app.route('/admin/registration/<int:id>')", "@app.route('/admin/registration/<int:id>')")
content = content.replace("@app.route('/admin/registration/<int:id>/edit', methods=['POST']')", "@app.route('/admin/registration/<int:id>/edit', methods=['POST'])")
content = content.replace("@app.route('/admin/registration/<int:id>/delete')", "@app.route('/admin/registration/<int:id>/delete')")

with open('app.py', 'w') as f:
    f.write(content)

print('Fixed column definitions')
