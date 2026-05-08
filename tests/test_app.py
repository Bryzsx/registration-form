import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, Admin, Church, Registration

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            # Create test admin
            admin = Admin(username='testadmin')
            admin.set_password('testpass')
            db.session.add(admin)
            # Create test church
            church = Church(name='Test Church')
            db.session.add(church)
            # Create test zone
            from app import Zone
            zone = Zone(name='Test Zone')
            db.session.add(zone)
            db.session.commit()
            yield client
            db.session.remove()
            db.drop_all()

def test_home_page(client):
    """Test that home page loads"""
    response = client.get('/')
    assert response.status_code == 200

def test_register_page(client):
    """Test that register page loads"""
    response = client.get('/register')
    assert response.status_code == 200

def test_login_page(client):
    """Test that login page loads"""
    response = client.get('/login')
    assert response.status_code == 200

def test_admin_login(client):
    """Test admin login functionality"""
    response = client.post('/login', data={
        'username': 'testadmin',
        'password': 'testpass'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Overview' in response.data

def test_invalid_login(client):
    """Test invalid login attempt"""
    response = client.post('/login', data={
        'username': 'wrong',
        'password': 'wrong'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Invalid username or password' in response.data

def test_registration_validation(client):
    """Test registration form validation"""
    # Test with invalid data
    response = client.post('/register', data={
        'first_name': '123',  # Invalid - numbers
        'last_name': 'Doe',
        'gender': 'Male',
        'birth_date': '2000-01-01',
        'church_id': '1'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'must contain only letters' in response.data

def test_valid_registration(client):
    """Test valid registration"""
    response = client.post('/register', data={
        'first_name': 'John',
        'last_name': 'Doe',
        'gender': 'Male',
        'age': '26',
        'church_id': '1',
        'zone_id': '1'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'REG-' in response.data

def test_form_persistence_on_error(client):
    """Test form data persists on validation error"""
    response = client.post('/register', data={
        'first_name': '123',
        'last_name': 'Doe',
        'gender': 'Male',
        'age': '',
        'church_id': '1'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Doe' in response.data

def test_admin_delete_registration_post(client):
    """Test admin can delete registration via POST"""
    client.post('/login', data={
        'username': 'testadmin',
        'password': 'testpass'
    })
    reg_resp = client.post('/register', data={
        'first_name': 'Delete',
        'last_name': 'Test',
        'gender': 'Male',
        'age': '20',
        'church_id': '1',
        'zone_id': '1'
    }, follow_redirects=True)
    assert b'REG-' in reg_resp.data
    
    reg = Registration.query.filter_by(first_name='Delete').first()
    assert reg is not None
    resp = client.post(f'/admin/registration/{reg.id}/delete', follow_redirects=True)
    assert resp.status_code == 200
    deleted = Registration.query.filter_by(first_name='Delete').first()
    assert deleted is None
