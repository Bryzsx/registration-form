from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime, timedelta
import pandas as pd
import io
import hashlib
import os

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-this-in-production')

# Database configuration
database_url = os.environ.get('DATABASE_URL')

# Fallback to local SQLite if environment variable is missing or external DB is blocked
if not database_url:
    database_url = 'sqlite:///registrations.db'
elif 'supabase.co' in database_url:
    # Supabase requires SSL and specific pooling, but free PythonAnywhere blocks port 5432
    database_url = 'sqlite:///registrations.db'

# Supabase requires SSL and connection pooling
if 'supabase.co' in database_url and 'sslmode' not in database_url:
    database_url += '?sslmode=require'

app.config['SQLALCHEMY_DATABASE_URI'] = database_url

# Connection pooling for Supabase (3000 users)
if 'supabase.co' in database_url:
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 10,
        'max_overflow': 20,
        'pool_recycle': 280,
        'pool_pre_ping': True,
    }

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    
    def set_password(self, password):
        self.password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    def check_password(self, password):
        return self.password_hash == hashlib.sha256(password.encode()).hexdigest()

class Church(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True, nullable=False)
    registrations = db.relationship('Registration', backref='church', lazy=True)

class Registration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    middle_name = db.Column(db.String(100), nullable=True)
    gender = db.Column(db.String(10), nullable=False, server_default='Not Specified')
    birth_date = db.Column(db.Date, nullable=False)
    age = db.Column(db.Integer, nullable=False)
    church_name = db.Column(db.String(200), nullable=False)
    church_id = db.Column(db.Integer, db.ForeignKey('church.id'), nullable=True)
    registration_code = db.Column(db.String(50), unique=True, nullable=False)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    def calculate_age(self):
        today = datetime.today()
        return today.year - self.birth_date.year - ((today.month, today.day) < (self.birth_date.month, self.birth_date.day))

def generate_registration_code():
    last_reg = Registration.query.order_by(Registration.id.desc()).first()
    if last_reg:
        last_num = int(last_reg.registration_code.split('-')[-1])
        new_num = last_num + 1
    else:
        new_num = 1
    return f"REG-{new_num:04d}"

@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    churches = Church.query.order_by(Church.name).all()
    
    if request.method == 'POST':
        data = request.form
        birth_date = datetime.strptime(data['birth_date'], '%Y-%m-%d').date()
        
        church_id = data.get('church_id')
        church_name = ''
        if church_id:
            church = Church.query.get(int(church_id))
            if church:
                church_name = church.name
        
        reg = Registration(
            first_name=data['first_name'],
            last_name=data['last_name'],
            middle_name=data.get('middle_name', ''),
            gender=data.get('gender', 'Not Specified'),
            birth_date=birth_date,
            age=0,
            church_name=church_name,
            church_id=int(church_id) if church_id else None,
            registration_code=generate_registration_code()
        )
        reg.age = reg.calculate_age()
        
        db.session.add(reg)
        db.session.commit()
        
        return render_template('success.html', registration=reg)
    
    return render_template('register.html', churches=churches)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        admin = Admin.query.filter_by(username=username).first()
        
        if admin and admin.check_password(password):
            login_user(admin)
            return redirect(url_for('admin'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/admin')
@login_required
def admin():
    registrations = Registration.query
    search = request.args.get('search', '')
    church_filter = request.args.get('church', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    if search:
        registrations = registrations.filter(
            (Registration.first_name.contains(search)) |
            (Registration.last_name.contains(search)) |
            (Registration.registration_code.contains(search)) |
            (Registration.church_name.contains(search))
        )
    
    if church_filter:
        registrations = registrations.filter(Registration.church_name == church_filter)
    
    if date_from:
        registrations = registrations.filter(Registration.registration_date >= datetime.strptime(date_from, '%Y-%m-%d'))
    
    if date_to:
        registrations = registrations.filter(Registration.registration_date <= datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1))
    
    registrations = registrations.order_by(Registration.registration_date.desc()).all()
    
    churches = db.session.query(Registration.church_name).distinct().all()
    churches = [c[0] for c in churches]
    
    total = Registration.query.count()
    today = Registration.query.filter(Registration.registration_date >= datetime.now().date()).count()
    
    age_groups = {
        '0-18': Registration.query.filter(Registration.age <= 18).count(),
        '19-30': Registration.query.filter(Registration.age.between(19, 30)).count(),
        '31-50': Registration.query.filter(Registration.age.between(31, 50)).count(),
        '51+': Registration.query.filter(Registration.age > 50).count()
    }
    
    all_churches = Church.query.order_by(Church.name).all()
    
    return render_template('admin.html', 
                         registrations=registrations, 
                         churches=churches,
                         total=total,
                         today=today,
                         age_groups=age_groups,
                         search=search,
                         church_filter=church_filter,
                         date_from=date_from,
                         date_to=date_to,
                         all_churches=all_churches)

@app.route('/admin/church/add', methods=['POST'])
@login_required
def add_church():
    name = request.form.get('church_name')
    if name:
        existing = Church.query.filter_by(name=name).first()
        if not existing:
            church = Church(name=name)
            db.session.add(church)
            db.session.commit()
            flash('Church added successfully', 'success')
        else:
            flash('Church already exists', 'warning')
    return redirect(url_for('admin'))

@app.route('/admin/church/<int:id>/delete')
@login_required
def delete_church(id):
    church = Church.query.get_or_404(id)
    db.session.delete(church)
    db.session.commit()
    flash('Church deleted successfully', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/registration/<int:id>')
@login_required
def get_registration(id):
    reg = Registration.query.get_or_404(id)
    return jsonify({
        'id': reg.id,
        'first_name': reg.first_name,
        'last_name': reg.last_name,
        'middle_name': reg.middle_name,
        'gender': reg.gender,
        'birth_date': reg.birth_date.strftime('%Y-%m-%d'),
        'age': reg.age,
        'church_name': reg.church_name,
        'registration_code': reg.registration_code,
        'registration_date': reg.registration_date.strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/admin/registration/<int:id>/edit', methods=['POST'])
@login_required
def edit_registration(id):
    reg = Registration.query.get_or_404(id)
    data = request.form
    
    reg.first_name = data['first_name']
    reg.last_name = data['last_name']
    reg.middle_name = data.get('middle_name', '')
    reg.gender = data.get('gender', reg.gender)
    reg.birth_date = datetime.strptime(data['birth_date'], '%Y-%m-%d').date()
    reg.age = reg.calculate_age()
    
    church_id = data.get('church_id')
    if church_id:
        church = Church.query.get(int(church_id))
        if church:
            reg.church_name = church.name
            reg.church_id = church.id
    else:
        reg.church_name = data.get('church_name', reg.church_name)
        reg.church_id = None
    
    db.session.commit()
    flash('Registration updated successfully', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/registration/<int:id>/delete', methods=['GET', 'POST'])
@login_required
def delete_registration(id):
    reg = Registration.query.get_or_404(id)
    db.session.delete(reg)
    db.session.commit()
    flash('Registration deleted successfully', 'success')
    return redirect(url_for('admin'))

@app.route('/api/calculate-age', methods=['POST'])
def calculate_age():
    birth_date = datetime.strptime(request.json['birth_date'], '%Y-%m-%d').date()
    today = datetime.today()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return jsonify({'age': age})

@app.route('/export')
@login_required
def export_excel():
    registrations = Registration.query.all()
    
    data = []
    for reg in registrations:
        data.append({
            'Registration Code': reg.registration_code,
            'First Name': reg.first_name,
            'Last Name': reg.last_name,
            'Middle Name': reg.middle_name,
            'Gender': reg.gender,
            'Birth Date': reg.birth_date.strftime('%Y-%m-%d'),
            'Age': reg.age,
            'Church Name': reg.church_name,
            'Registration Date': reg.registration_date.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    df = pd.DataFrame(data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Registrations', index=False)
    
    output.seek(0)
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'registrations_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    )

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Create admin if not exists
        if not Admin.query.filter_by(username='admin').first():
            admin = Admin(username='admin')
            admin.set_password('admin123')
            db.session.add(admin)
        
        # Pre-populate churches
        default_churches = ['NLC Main (Central Zone)', 'NLCF Gingoog (West Zone)']
        for church_name in default_churches:
            if not Church.query.filter_by(name=church_name).first():
                church = Church(name=church_name)
                db.session.add(church)
        
        db.session.commit()
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
