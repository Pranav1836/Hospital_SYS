from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # patient, nurse, doctor, admin
    full_name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    phone = db.Column(db.String(15))

class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))
    phone = db.Column(db.String(15))
    email = db.Column(db.String(100))
    address = db.Column(db.Text)
    disease_taxonomy = db.Column(db.String(200))
    account_balance = db.Column(db.Float, default=0.0)
    family_patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=True)
    family_relation = db.Column(db.String(50))
    admission_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    family_member = db.relationship('Patient', remote_side=[id], backref='related_patients')

# Initialize database
with app.app_context():
    db.create_all()
    # Create default admin if not exists
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            password=generate_password_hash('admin123'),
            role='admin',
            full_name='System Administrator',
            email='admin@hospital.com'
        )
        db.session.add(admin)
        db.session.commit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login/<role>', methods=['GET', 'POST'])
def login(role):
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username, role=role).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['role'] = user.role
            session['username'] = user.username
            flash(f'Welcome {username}!', 'success')
            return redirect(url_for(f'{role}_dashboard'))
        else:
            flash('Invalid credentials!', 'danger')
    
    return render_template('login.html', role=role)

@app.route('/register/patient', methods=['GET', 'POST'])
def register_patient():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        full_name = request.form['full_name']
        age = request.form['age']
        gender = request.form['gender']
        phone = request.form['phone']
        email = request.form['email']
        address = request.form['address']
        disease_taxonomy = request.form['disease_taxonomy']
        account_balance = float(request.form['account_balance'])
        family_patient_id = request.form.get('family_patient_id')
        family_relation = request.form.get('family_relation')
        
        # Check if username exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists!', 'danger')
            return redirect(url_for('register_patient'))
        
        # Create user
        new_user = User(
            username=username,
            password=generate_password_hash(password),
            role='patient',
            full_name=full_name,
            email=email,
            phone=phone
        )
        db.session.add(new_user)
        db.session.commit()
        
        # Create patient profile
        new_patient = Patient(
            user_id=new_user.id,
            full_name=full_name,
            age=age,
            gender=gender,
            phone=phone,
            email=email,
            address=address,
            disease_taxonomy=disease_taxonomy,
            account_balance=account_balance,
            family_patient_id=int(family_patient_id) if family_patient_id else None,
            family_relation=family_relation
        )
        db.session.add(new_patient)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login', role='patient'))
    
    # Get all patients for family relation
    patients = Patient.query.all()
    return render_template('register_patient.html', patients=patients)

@app.route('/patient/dashboard')
def patient_dashboard():
    if 'user_id' not in session or session['role'] != 'patient':
        flash('Please login first!', 'warning')
        return redirect(url_for('login', role='patient'))
    
    patient = Patient.query.filter_by(user_id=session['user_id']).first()
    return render_template('patient_dashboard.html', patient=patient)

@app.route('/nurse/dashboard')
def nurse_dashboard():
    if 'user_id' not in session or session['role'] != 'nurse':
        flash('Please login first!', 'warning')
        return redirect(url_for('login', role='nurse'))
    
    patients = Patient.query.all()
    return render_template('nurse_dashboard.html', patients=patients)

@app.route('/doctor/dashboard')
def doctor_dashboard():
    if 'user_id' not in session or session['role'] != 'doctor':
        flash('Please login first!', 'warning')
        return redirect(url_for('login', role='doctor'))
    
    patients = Patient.query.all()
    return render_template('doctor_dashboard.html', patients=patients)

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user_id' not in session or session['role'] != 'admin':
        flash('Please login first!', 'warning')
        return redirect(url_for('login', role='admin'))
    
    patients = Patient.query.all()
    users = User.query.all()
    return render_template('admin_dashboard.html', patients=patients, users=users)

@app.route('/admin/register_staff', methods=['GET', 'POST'])
def register_staff():
    if 'user_id' not in session or session['role'] != 'admin':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']  # doctor or nurse
        full_name = request.form['full_name']
        email = request.form['email']
        phone = request.form['phone']
        
        # Check if username exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists!', 'danger')
            return redirect(url_for('register_staff'))
        
        # Create staff user
        new_user = User(
            username=username,
            password=generate_password_hash(password),
            role=role,
            full_name=full_name,
            email=email,
            phone=phone
        )
        db.session.add(new_user)
        db.session.commit()
        
        flash(f'{role.capitalize()} registered successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('register_staff.html')

@app.route('/admin/delete_patient/<int:patient_id>', methods=['POST'])
def delete_patient(patient_id):
    if 'user_id' not in session or session['role'] != 'admin':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('index'))
    
    patient = Patient.query.get_or_404(patient_id)
    user = User.query.get(patient.user_id)
    
    db.session.delete(patient)
    if user:
        db.session.delete(user)
    db.session.commit()
    
    flash('Patient deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'user_id' not in session or session['role'] != 'admin':
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(user_id)
    
    # Prevent deleting admin
    if user.role == 'admin':
        flash('Cannot delete admin user!', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    # If patient, delete patient profile too
    if user.role == 'patient':
        patient = Patient.query.filter_by(user_id=user_id).first()
        if patient:
            db.session.delete(patient)
    
    db.session.delete(user)
    db.session.commit()
    
    flash('User deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'info')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)