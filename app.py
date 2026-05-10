from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import pandas as pd
import io
import os
import logging

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-this-in-production')

# Logging
if not app.debug:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
else:
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')

# Database configuration
basedir = os.path.abspath(os.path.dirname(__file__))
database_url = os.environ.get('DATABASE_URL')

if database_url and ('postgres' in database_url or 'supabase' in database_url):
    if 'sslmode' not in database_url:
        database_url += '?sslmode=require'
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_size': 10,
        'max_overflow': 20,
        'pool_recycle': 280,
        'pool_pre_ping': True,
    }
else:
    database_url = f'sqlite:///{os.path.join(basedir, "instance", "registrations.db")}'
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url

db = SQLAlchemy(app)

# SQLite performance pragmas — WAL mode for concurrent reads/writes
if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']:
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'connect_args': {'check_same_thread': False},
        'pool_pre_ping': True,
    }

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

class Admin(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Zone(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True, nullable=False)

class Church(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True, nullable=False)
    registrations = db.relationship('Registration', backref='church', lazy=True)

class Registration(db.Model):
    __table_args__ = (
        db.Index('idx_registration_date', 'registration_date'),
        db.Index('idx_church_name', 'church_name'),
    )
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    gender = db.Column(db.String(10), nullable=False, server_default='Not Specified')
    age = db.Column(db.Integer, nullable=False)
    church_name = db.Column(db.String(200), nullable=False)
    church_id = db.Column(db.Integer, db.ForeignKey('church.id'), nullable=True)
    zone_id = db.Column(db.Integer, db.ForeignKey('zone.id'), nullable=True)
    registration_code = db.Column(db.String(50), unique=True, nullable=False)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    @property
    def zone_name(self):
        if self.zone_id:
            zone = db.session.get(Zone, self.zone_id)
            if zone:
                return zone.name
        return ''

def generate_registration_code():
    return None  # Set after flush in the route

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Admin, int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    churches = Church.query.order_by(Church.name).all()
    zones = Zone.query.order_by(Zone.name).all()
    
    if request.method == 'POST':
        data = request.form
        
        zone_id = data.get('zone_id')
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        gender = data.get('gender', '')
        age_str = data.get('age', '')
        church_id = data.get('church_id')
        
        errors = []
        
        if not first_name or not first_name.replace(' ', '').isalpha():
            errors.append('First name must contain only letters')
        
        if not last_name or not last_name.replace(' ', '').isalpha():
            errors.append('Last name must contain only letters')
        
        if gender not in ['Male', 'Female']:
            errors.append('Gender must be Male or Female')
        
        age = None
        if not age_str:
            errors.append('Age is required')
        else:
            try:
                age = int(age_str)
                if age < 0 or age > 120:
                    errors.append('Invalid age')
            except ValueError:
                errors.append('Age must be a number')
        
        if not church_id:
            errors.append('Church fellowship is required')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('register.html', churches=churches, zones=zones, data=data)
        
        try:
            church_name = ''
            if church_id:
                church = db.session.get(Church, int(church_id))
                if church:
                    church_name = church.name
            
            reg = Registration(
                first_name=first_name,
                last_name=last_name,
                gender=gender,
                age=age,
                church_name=church_name,
                church_id=int(church_id) if church_id else None,
                zone_id=int(zone_id) if zone_id else None,
                registration_code=''
            )
            
            db.session.add(reg)
            db.session.flush()
            reg.registration_code = f"REG-{reg.id:04d}"
            db.session.commit()
            
            return render_template('success.html', registration=reg)
        except Exception as e:
            db.session.rollback()
            logging.error(f'Registration error: {str(e)}')
            flash('An error occurred during registration. Please try again.', 'danger')
            return render_template('register.html', churches=churches, zones=zones, data=data)
    
    return render_template('register.html', churches=churches, zones=zones, data={})

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
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
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
    
    registrations = registrations.order_by(Registration.registration_date.desc())
    pagination = registrations.paginate(page=page, per_page=per_page, error_out=False)
    registrations = pagination.items
    
    churches = db.session.query(Registration.church_name).distinct().all()
    churches = [c[0] for c in churches]
    
    total = Registration.query.count()
    today = Registration.query.filter(Registration.registration_date >= datetime.combine(datetime.now().date(), datetime.min.time())).count()
    
    age_counts = db.session.query(
        db.case((Registration.age <= 18, '0-18'),
                (Registration.age.between(19, 30), '19-30'),
                (Registration.age.between(31, 50), '31-50'),
                else_='51+').label('group'),
        db.func.count(Registration.id)
    ).group_by('group').all()
    age_groups = {'0-18': 0, '19-30': 0, '31-50': 0, '51+': 0}
    for group, count in age_counts:
        age_groups[group] = count
    
    all_churches = Church.query.order_by(Church.name).all()
    all_zones = Zone.query.order_by(Zone.name).all()
    zone_map = {z.id: z.name for z in all_zones}
    
    for reg in registrations:
        reg._zone_name = zone_map.get(reg.zone_id, '') if reg.zone_id else ''
    
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
                         all_churches=all_churches,
                         all_zones=all_zones,
                         zone_map=zone_map,
                         pagination=pagination)

@app.route('/admin/church/add', methods=['POST'])
@login_required
def add_church():
    try:
        name = request.form.get('church_name', '').strip()
        if not name:
            flash('Church name is required', 'warning')
            return redirect(url_for('admin'))
        
        existing = Church.query.filter_by(name=name).first()
        if not existing:
            church = Church(name=name)
            db.session.add(church)
            db.session.commit()
            flash('Church added successfully', 'success')
        else:
            flash('Church already exists', 'warning')
    except Exception as e:
        db.session.rollback()
        logging.error(f'Add church error: {str(e)}')
        flash('An error occurred. Please try again.', 'danger')
    
    return redirect(url_for('admin'))

@app.route('/admin/church/<int:id>/delete', methods=['POST'])
@login_required
def delete_church(id):
    try:
        church = db.session.get(Church, id)
        if church:
            db.session.delete(church)
            db.session.commit()
            flash('Church deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        logging.error(f'Delete church error: {str(e)}')
        flash('An error occurred. Please try again.', 'danger')
    
    return redirect(url_for('admin'))

@app.route('/admin/zone/add', methods=['POST'])
@login_required
def add_zone():
    try:
        name = request.form.get('zone_name', '').strip()
        if not name:
            flash('Zone name is required', 'warning')
            return redirect(url_for('admin'))
        
        existing = Zone.query.filter_by(name=name).first()
        if not existing:
            zone = Zone(name=name)
            db.session.add(zone)
            db.session.commit()
            flash('Zone added successfully', 'success')
        else:
            flash('Zone already exists', 'warning')
    except Exception as e:
        db.session.rollback()
        logging.error(f'Add zone error: {str(e)}')
        flash('An error occurred. Please try again.', 'danger')
    
    return redirect(url_for('admin'))

@app.route('/admin/zone/<int:id>/edit', methods=['POST'])
@login_required
def edit_zone(id):
    try:
        zone = db.session.get(Zone, id)
        if not zone:
            flash('Zone not found', 'danger')
            return redirect(url_for('admin'))
        
        new_name = request.form.get('zone_name', '').strip()
        if not new_name:
            flash('Zone name is required', 'warning')
            return redirect(url_for('admin'))
        
        existing = Zone.query.filter(Zone.name == new_name, Zone.id != id).first()
        if existing:
            flash('Zone name already exists', 'warning')
        else:
            zone.name = new_name
            db.session.commit()
            flash('Zone updated successfully', 'success')
    except Exception as e:
        db.session.rollback()
        logging.error(f'Edit zone error: {str(e)}')
        flash('An error occurred. Please try again.', 'danger')
    
    return redirect(url_for('admin'))

@app.route('/admin/zone/<int:id>/delete', methods=['POST'])
@login_required
def delete_zone(id):
    try:
        zone = db.session.get(Zone, id)
        if zone:
            db.session.delete(zone)
            db.session.commit()
            flash('Zone deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        logging.error(f'Delete zone error: {str(e)}')
        flash('An error occurred. Please try again.', 'danger')
    
    return redirect(url_for('admin'))

@app.route('/admin/registration/<int:id>')
@login_required
def get_registration(id):
    reg = Registration.query.get_or_404(id)
    all_zones = {z.id: z.name for z in Zone.query.all()}
    zone_name = all_zones.get(reg.zone_id, '') if reg.zone_id else ''
    return jsonify({
        'id': reg.id,
        'first_name': reg.first_name,
        'last_name': reg.last_name,
        'gender': reg.gender,
        'age': reg.age,
        'church_name': reg.church_name,
        'zone_name': zone_name,
        'zone_id': reg.zone_id,
        'registration_code': reg.registration_code,
        'registration_date': reg.registration_date.strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/admin/registration/<int:id>/edit', methods=['POST'])
@login_required
def edit_registration(id):
    try:
        reg = db.session.get(Registration, id)
        if not reg:
            flash('Registration not found', 'danger')
            return redirect(url_for('admin'))
        
        data = request.form
        
        # Validation
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        
        if not first_name or not first_name.replace(' ', '').isalpha():
            flash('First name must contain only letters', 'danger')
            return redirect(url_for('admin'))
        
        if not last_name or not last_name.replace(' ', '').isalpha():
            flash('Last name must contain only letters', 'danger')
            return redirect(url_for('admin'))
        
        reg.first_name = first_name
        reg.last_name = last_name
        reg.gender = data.get('gender', reg.gender)
        
        age_str = data.get('age', '')
        if age_str:
            try:
                age_val = int(age_str)
                if 0 <= age_val <= 120:
                    reg.age = age_val
            except ValueError:
                pass
        
        zone_id = data.get('zone_id')
        if zone_id and zone_id != 'none':
            reg.zone_id = int(zone_id)
        else:
            reg.zone_id = None
        
        church_id = data.get('church_id')
        if church_id:
            church = db.session.get(Church, int(church_id))
            if church:
                reg.church_name = church.name
                reg.church_id = church.id
        else:
            reg.church_name = data.get('church_name', reg.church_name)
            reg.church_id = None
        
        db.session.commit()
        flash('Registration updated successfully', 'success')
    except Exception as e:
        db.session.rollback()
        logging.error(f'Edit registration error: {str(e)}')
        flash('An error occurred. Please try again.', 'danger')
    
    return redirect(url_for('admin'))

@app.route('/admin/registration/<int:id>/delete', methods=['POST'])
@login_required
def delete_registration(id):
    try:
        reg = db.session.get(Registration, id)
        if reg:
            db.session.delete(reg)
            db.session.commit()
            flash('Registration deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        logging.error(f'Delete registration error: {str(e)}')
        flash('An error occurred. Please try again.', 'danger')
    
    return redirect(url_for('admin'))

@app.route('/export')
@login_required
def export_excel():
    try:
        registrations = Registration.query.all()
        all_zones = {z.id: z.name for z in Zone.query.all()}
        
        data = []
        for reg in registrations:
            zone_name = all_zones.get(reg.zone_id, '') if reg.zone_id else ''
            data.append({
                'Registration Code': reg.registration_code,
                'First Name': reg.first_name,
                'Last Name': reg.last_name,
                'Gender': reg.gender,
                'Age': reg.age,
                'Church Name': reg.church_name,
                'Zone': zone_name,
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
    except Exception as e:
        logging.error(f'Export error: {str(e)}')
        flash('An error occurred during export. Please try again.', 'danger')
        return redirect(url_for('admin'))

@app.route('/health')
def health():
    return jsonify({'status': 'ok', 'timestamp': datetime.utcnow().isoformat()})

@app.after_request
def add_security_headers(response):
    if request.path.startswith('/static/'):
        response.cache_control.max_age = 3600
        response.cache_control.public = True
    return response

@app.errorhandler(404)
def not_found(e):
    return render_template('base.html', title='404 - Page Not Found'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('base.html', title='500 - Server Error'), 500

with app.app_context():
    from sqlalchemy import event as _event
    
    if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']:
        @_event.listens_for(db.engine, 'connect')
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA cache_size=-64000")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    
    db.create_all()
    # Create admin if not exists
    if not Admin.query.filter_by(username='admin').first():
        default_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
        admin = Admin(username='admin')
        admin.set_password(default_password)
        db.session.add(admin)
        if default_password == 'admin123':
            logging.warning('Default admin password in use. Set ADMIN_PASSWORD env var in production.')
    
    # Pre-populate churches
    default_churches = ['NLC Main (Central Zone)', 'NLCF Gingoog (West Zone)']
    for church_name in default_churches:
        if not Church.query.filter_by(name=church_name).first():
            church = Church(name=church_name)
            db.session.add(church)
    
    # Pre-populate zones
    default_zones = ['Central Zone', 'Eastern Zone', 'Western Zone', 'Mother Church']
    for zone_name in default_zones:
        if not Zone.query.filter_by(name=zone_name).first():
            zone = Zone(name=zone_name)
            db.session.add(zone)
    
    db.session.commit()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logging.info(f'Starting Flask dev server on port {port}')
    app.run(host='0.0.0.0', port=port, threaded=True)
