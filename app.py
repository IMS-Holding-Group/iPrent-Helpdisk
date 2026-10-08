from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps
import os
import re
import random
import threading
import time
from config import SQLALCHEMY_DATABASE_URI, SECRET_KEY, BASE_DIR

ROLES = ('admin', 'support', 'employee')
STAFF_ROLES = ('admin', 'support')

# Attempt to import SNMP library (optional)
try:
    from pysnmp.hlapi import *
    SNMP_AVAILABLE = True
except ImportError:
    SNMP_AVAILABLE = False
    print("Warning: pysnmp library not available. SNMP monitoring will be disabled.")

# Import trained AI model
try:
    from ai_model import AITicketModel
    ai_model = AITicketModel()
    # Attempt to load trained model
    if ai_model.load_model('models'):
        print("AI model loaded successfully")
        AI_MODEL_AVAILABLE = True
    else:
        print("Warning: AI model not trained. Fallback system will be used.")
        AI_MODEL_AVAILABLE = False
except ImportError as e:
    print(f"Warning: Cannot import ai_model: {e}")
    AI_MODEL_AVAILABLE = False
    ai_model = None
except Exception as e:
    print(f"Warning: Error loading AI model: {e}")
    AI_MODEL_AVAILABLE = False
    ai_model = None

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = SECRET_KEY

db = SQLAlchemy(app)

# Database models
class Printer(db.Model):
    __tablename__ = 'printers'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.Text, nullable=False)
    ip_address = db.Column(db.Text, nullable=True)
    model = db.Column(db.Text, nullable=True)
    status = db.Column(db.Text, nullable=False, default='offline')
    ink_level = db.Column(db.Integer, default=100)
    last_seen = db.Column(db.DateTime, nullable=True)

class Ticket(db.Model):
    __tablename__ = 'tickets'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    printer_id = db.Column(db.Integer, db.ForeignKey('printers.id', ondelete='SET NULL'), nullable=True)
    # Generalize system to include all types of IT problems
    ticket_type = db.Column(db.Text, default='printer')  # 'printer', 'network', 'hardware', 'software', 'other'
    device_name = db.Column(db.Text, nullable=True)  # Name of affected device or system
    affected_users_count = db.Column(db.Integer, default=1)  # Number of affected users
    reporter_email = db.Column(db.Text, nullable=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    title = db.Column(db.Text, nullable=True)
    description = db.Column(db.Text, nullable=True)
    priority = db.Column(db.Text, default='Low')  # 'Low', 'Medium', 'High', 'Critical'
    status = db.Column(db.Text, default='Open')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TicketComment(db.Model):
    __tablename__ = 'ticket_comments'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('tickets.id', ondelete='CASCADE'), nullable=False)
    author = db.Column(db.Text, nullable=True)
    message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.Text, unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    role = db.Column(db.Text, default='employee')  # admin, support, employee
    email = db.Column(db.Text, nullable=True)

class Alert(db.Model):
    __tablename__ = 'alerts'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    printer_id = db.Column(db.Integer, db.ForeignKey('printers.id', ondelete='CASCADE'), nullable=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('tickets.id', ondelete='CASCADE'), nullable=True)
    alert_type = db.Column(db.Text, nullable=False)  # 'low_ink', 'offline', 'high_priority', 'maintenance_due'
    message = db.Column(db.Text, nullable=True)
    severity = db.Column(db.Text, default='medium')  # 'low', 'medium', 'high', 'critical'
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class MaintenanceSchedule(db.Model):
    __tablename__ = 'maintenance_schedules'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    printer_id = db.Column(db.Integer, db.ForeignKey('printers.id', ondelete='CASCADE'), nullable=False)
    maintenance_type = db.Column(db.Text, nullable=False)  # 'cleaning', 'inspection', 'repair', 'replacement'
    scheduled_date = db.Column(db.DateTime, nullable=False)
    completed_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.Text, default='scheduled')  # 'scheduled', 'completed', 'cancelled'
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class InkPrediction(db.Model):
    __tablename__ = 'ink_predictions'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    printer_id = db.Column(db.Integer, db.ForeignKey('printers.id', ondelete='CASCADE'), nullable=False)
    current_level = db.Column(db.Integer, nullable=False)
    predicted_depletion_date = db.Column(db.DateTime, nullable=False)
    confidence_score = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class TicketCategory(db.Model):
    __tablename__ = 'ticket_categories'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('tickets.id', ondelete='CASCADE'), nullable=False)
    category = db.Column(db.Text, nullable=False)  # 'hardware', 'software', 'network', 'ink', 'paper', 'printer', 'other'
    confidence = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# New model to store AI automatic responses
class AIResponse(db.Model):
    __tablename__ = 'ai_responses'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('tickets.id', ondelete='CASCADE'), nullable=False)
    initial_response = db.Column(db.Text, nullable=False)  # Initial automatic response
    troubleshooting_steps = db.Column(db.Text, nullable=True)  # Initial troubleshooting steps
    common_solutions = db.Column(db.Text, nullable=True)  # Common solutions
    guidance = db.Column(db.Text, nullable=True)  # Guidance before support team intervention
    confidence_score = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Model to track devices and systems
class Device(db.Model):
    __tablename__ = 'devices'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.Text, nullable=False)
    device_type = db.Column(db.Text, nullable=False)  # 'printer', 'server', 'workstation', 'network_device', 'software'
    ip_address = db.Column(db.Text, nullable=True)
    location = db.Column(db.Text, nullable=True)
    status = db.Column(db.Text, default='unknown')  # 'online', 'offline', 'warning', 'error'
    last_seen = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# AI and natural language processing functions
def predict_ink_depletion(printer_id, current_level, usage_history=None):
    # Advanced algorithm for predicting ink depletion
    if current_level <= 0:
        return None, 0.0
    
    # Calculate consumption rate based on current ink level
    # Lower ink means faster consumption
    base_consumption = 2.0
    if current_level < 20:
        consumption_multiplier = 1.5
    elif current_level < 50:
        consumption_multiplier = 1.2
    else:
        consumption_multiplier = 1.0
    
    # Add random variation for realism
    daily_consumption = base_consumption * consumption_multiplier * random.uniform(0.8, 1.2)
    
    days_until_depletion = current_level / daily_consumption
    predicted_date = datetime.utcnow() + timedelta(days=int(days_until_depletion))
    
    # Calculate confidence score based on ink level and history
    # Lower ink means higher confidence
    base_confidence = 0.5
    level_factor = (100 - current_level) / 200
    time_factor = min(days_until_depletion / 30, 0.3)
    confidence = min(base_confidence + level_factor + time_factor, 0.95)
    
    return predicted_date, confidence

def get_user_role(user):
    role = getattr(user, 'role', None) or 'employee'
    if role not in ROLES:
        return 'admin' if user.username == 'admin' else 'employee'
    return role

def home_redirect():
    if session.get('role') == 'employee':
        return redirect(url_for('employee_portal'))
    return redirect(url_for('dashboard'))

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapped

def staff_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session.get('role') == 'employee':
            return redirect(url_for('employee_portal'))
        return view(*args, **kwargs)
    return wrapped

def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return view(*args, **kwargs)
    return wrapped

def user_can_access_ticket(ticket):
    if session.get('role') in STAFF_ROLES:
        return True
    return ticket.created_by_user_id == session.get('user_id')

def seed_default_users():
    default_users = [
        {'username': 'admin', 'password': '', 'role': 'admin', 'email': 'admin@helpdesk.local'},
        {'username': 'support', 'password': 'support123', 'role': 'support', 'email': 'support@helpdesk.local'},
        {'username': 'employee', 'password': 'employee123', 'role': 'employee', 'email': 'employee@company.local'},
    ]
    for entry in default_users:
        user = User.query.filter_by(username=entry['username']).first()
        if user is None:
            db.session.add(User(
                username=entry['username'],
                password_hash=generate_password_hash(entry['password']),
                role=entry['role'],
                email=entry['email'],
            ))
        else:
            if not getattr(user, 'role', None) or user.role not in ROLES:
                user.role = entry['role']
            if not user.email:
                user.email = entry['email']
    db.session.commit()

# Initialize database and insert sample data
def init_db():
    with app.app_context():
        db.create_all()
        
        seed_default_users()

        # Check for default printers
        if Printer.query.count() == 0:
            printers = [
                Printer(name='Main Office Printer', ip_address='192.168.1.100', model='HP LaserJet Pro M404dn', status='online', ink_level=75, last_seen=datetime.utcnow()),
                Printer(name='Technical Department Printer', ip_address='192.168.1.101', model='Canon PIXMA TR8620', status='online', ink_level=45, last_seen=datetime.utcnow()),
                Printer(name='Reception Printer', ip_address='192.168.1.102', model='Epson WorkForce Pro WF-3720', status='offline', ink_level=90, last_seen=None),
                Printer(name='Management Printer', ip_address='192.168.1.103', model='Brother HL-L2350DW', status='online', ink_level=60, last_seen=datetime.utcnow()),
                Printer(name='Sales Printer', ip_address='192.168.1.104', model='HP OfficeJet Pro 9015', status='online', ink_level=30, last_seen=datetime.utcnow()),
                Printer(name='Accounting Printer', ip_address='192.168.1.105', model='Canon imageCLASS MF445dw', status='online', ink_level=85, last_seen=datetime.utcnow()),
                Printer(name='HR Printer', ip_address='192.168.1.106', model='Epson EcoTank ET-2720', status='offline', ink_level=95, last_seen=None),
                Printer(name='Warehouse Printer', ip_address='192.168.1.107', model='Brother MFC-L2750DW', status='online', ink_level=20, last_seen=datetime.utcnow()),
                Printer(name='Maintenance Printer', ip_address='192.168.1.108', model='HP LaserJet Enterprise M507dn', status='online', ink_level=50, last_seen=datetime.utcnow()),
                Printer(name='Meeting Room Printer', ip_address='192.168.1.109', model='Canon PIXMA G6020', status='offline', ink_level=70, last_seen=None)
            ]
            for printer in printers:
                db.session.add(printer)
            db.session.commit()
        
        # Add various devices (servers, workstations, network devices)
        if Device.query.count() == 0:
            devices = [
                Device(name='Main Database Server', device_type='server', ip_address='192.168.1.10', location='Server Room', status='online', last_seen=datetime.utcnow()),
                Device(name='Web Server', device_type='server', ip_address='192.168.1.11', location='Server Room', status='online', last_seen=datetime.utcnow()),
                Device(name='Email Server', device_type='server', ip_address='192.168.1.12', location='Server Room', status='online', last_seen=datetime.utcnow()),
                Device(name='Main Router', device_type='network_device', ip_address='192.168.1.1', location='Network Room', status='online', last_seen=datetime.utcnow()),
                Device(name='Main Switch', device_type='network_device', ip_address='192.168.1.2', location='Network Room', status='online', last_seen=datetime.utcnow()),
                Device(name='Firewall', device_type='network_device', ip_address='192.168.1.3', location='Network Room', status='online', last_seen=datetime.utcnow()),
                Device(name='Management Workstation', device_type='workstation', ip_address='192.168.1.50', location='Management Office', status='online', last_seen=datetime.utcnow()),
                Device(name='Sales Workstation', device_type='workstation', ip_address='192.168.1.51', location='Sales Department', status='online', last_seen=datetime.utcnow()),
            ]
            for device in devices:
                db.session.add(device)
            db.session.commit()
        
        # Check for default diverse tickets
        if Ticket.query.count() == 0:
            printer_ids = [p.id for p in Printer.query.all()]
            device_ids = [d.id for d in Device.query.all()]
            statuses = ['Open', 'In Progress', 'Resolved']
            priorities = ['Low', 'Medium', 'High', 'Critical']
            ticket_types = ['printer', 'network', 'hardware', 'software', 'other']
            
            # Diverse tickets for all types of problems
            tickets_data = [
                # Printer problems
                {'type': 'printer', 'title': 'Printer not responding to commands', 'description': 'Printer does not respond to print commands from any device on the network', 'priority': 'High', 'device': 'Main Office Printer', 'users': 5},
                {'type': 'printer', 'title': 'Frequent ink depletion', 'description': 'We notice ink runs out very quickly, there may be a consumption problem', 'priority': 'Medium', 'device': 'Technical Department Printer', 'users': 3},
                {'type': 'printer', 'title': 'Printing problem - unclear documents', 'description': 'Printer prints unclear and blurry documents, needs cleaning or ink replacement', 'priority': 'Medium', 'device': 'Reception Printer', 'users': 8},
                {'type': 'printer', 'title': 'Paper feed problem', 'description': 'Printer does not pull paper correctly, needs manual assistance', 'priority': 'High', 'device': 'Management Printer', 'users': 2},
                
                # Network problems
                {'type': 'network', 'title': 'Internet connection outage', 'description': 'All devices in the office cannot access the internet despite local connection working', 'priority': 'Critical', 'device': 'Main Router', 'users': 50},
                {'type': 'network', 'title': 'Severe network slowness', 'description': 'Network is very slow, file downloads take a long time', 'priority': 'High', 'device': 'Main Switch', 'users': 30},
                {'type': 'network', 'title': 'Server connection failure', 'description': 'Cannot access database server from some devices', 'priority': 'Critical', 'device': 'Main Database Server', 'users': 25},
                {'type': 'network', 'title': 'WiFi problem', 'description': 'Wireless connection is unstable, disconnects frequently', 'priority': 'High', 'device': 'Main Router', 'users': 15},
                {'type': 'network', 'title': 'IP Address problem', 'description': 'Some devices do not get IP address automatically', 'priority': 'Medium', 'device': 'Main Switch', 'users': 10},
                {'type': 'network', 'title': 'Connection outage between departments', 'description': 'Cannot access devices in other departments', 'priority': 'High', 'device': 'Main Switch', 'users': 20},
                
                # Hardware problems
                {'type': 'hardware', 'title': 'Workstation failure', 'description': 'Workstation does not work, no signal appears on screen', 'priority': 'High', 'device': 'Management Workstation', 'users': 1},
                {'type': 'hardware', 'title': 'Screen problem', 'description': 'Screen shows black lines and flickers constantly', 'priority': 'Medium', 'device': 'Sales Workstation', 'users': 1},
                {'type': 'hardware', 'title': 'High noise from server', 'description': 'Server makes loud and annoying sounds, problem may be in fan', 'priority': 'High', 'device': 'Main Database Server', 'users': 0},
                {'type': 'hardware', 'title': 'Keyboard problem', 'description': 'Some keys on keyboard do not work', 'priority': 'Low', 'device': 'Management Workstation', 'users': 1},
                {'type': 'hardware', 'title': 'Mouse problem', 'description': 'Mouse does not respond to commands correctly', 'priority': 'Low', 'device': 'Sales Workstation', 'users': 1},
                {'type': 'hardware', 'title': 'Hard drive failure', 'description': 'Hard drive in server does not work, may be damaged', 'priority': 'Critical', 'device': 'Web Server', 'users': 0},
                {'type': 'hardware', 'title': 'Power problem', 'description': 'Device shuts down suddenly, problem may be in power supply', 'priority': 'High', 'device': 'Management Workstation', 'users': 1},
                
                # Software problems
                {'type': 'software', 'title': 'Operating system crash', 'description': 'Windows does not start, shows blue screen on boot', 'priority': 'Critical', 'device': 'Management Workstation', 'users': 1},
                {'type': 'software', 'title': 'Software installation problem', 'description': 'Failed to install Office on new device', 'priority': 'Medium', 'device': 'Sales Workstation', 'users': 1},
                {'type': 'software', 'title': 'Severe system slowness', 'description': 'System is very slow, programs take long time to open', 'priority': 'High', 'device': 'Management Workstation', 'users': 1},
                {'type': 'software', 'title': 'Database problem', 'description': 'Database does not respond, applications do not work', 'priority': 'Critical', 'device': 'Main Database Server', 'users': 40},
                {'type': 'software', 'title': 'Email problem', 'description': 'Cannot send or receive email messages', 'priority': 'High', 'device': 'Email Server', 'users': 35},
                {'type': 'software', 'title': 'Application problem', 'description': 'Accounting application crashes frequently when used', 'priority': 'High', 'device': 'Management Workstation', 'users': 5},
                {'type': 'software', 'title': 'Update problem', 'description': 'Windows updates do not work, shows error message', 'priority': 'Medium', 'device': 'Sales Workstation', 'users': 1},
                {'type': 'software', 'title': 'Virus problem', 'description': 'Antivirus detects viruses but cannot remove them', 'priority': 'High', 'device': 'Management Workstation', 'users': 1},
                {'type': 'software', 'title': 'Backup problem', 'description': 'Backup system does not work, last backup failed', 'priority': 'Critical', 'device': 'Main Database Server', 'users': 0},
                {'type': 'software', 'title': 'Database query problem', 'description': 'Database query error, application does not work', 'priority': 'Critical', 'device': 'Main Database Server', 'users': 30},
                
                # Other problems
                {'type': 'other', 'title': 'Backup system problem', 'description': 'Backup system does not work correctly', 'priority': 'High', 'device': 'Main Database Server', 'users': 0},
                {'type': 'other', 'title': 'Security problem', 'description': 'Hacking attempt detected, needs immediate inspection', 'priority': 'Critical', 'device': 'Firewall', 'users': 0},
            ]
            
            emails = [
                'john@company.com', 'sarah@company.com', 'michael@company.com',
                'emily@company.com', 'david@company.com', 'jessica@company.com',
                'james@company.com', 'lisa@company.com', 'robert@company.com',
                'jennifer@company.com', 'william@company.com', 'amanda@company.com',
                'richard@company.com', 'linda@company.com', 'thomas@company.com'
            ]
            
            # Create diverse tickets
            for ticket_info in tickets_data:
                created_date = datetime.utcnow() - timedelta(days=random.randint(0, 30))
                status = random.choice(statuses)
                
                # Determine printer_id or device_name based on type
                printer_id = None
                device_name = ticket_info.get('device', None)
                
                if ticket_info['type'] == 'printer' and printer_ids:
                    printer_id = random.choice(printer_ids)
                    if not device_name:
                        printer = Printer.query.get(printer_id)
                        device_name = printer.name if printer else None
                
                ticket = Ticket(
                    printer_id=printer_id,
                    ticket_type=ticket_info['type'],
                    device_name=device_name,
                    affected_users_count=ticket_info.get('users', 1),
                    reporter_email=random.choice(emails),
                    title=ticket_info['title'],
                    description=ticket_info['description'],
                    priority=ticket_info['priority'],
                    status=status,
                    created_at=created_date,
                    updated_at=created_date + timedelta(hours=random.randint(1, 72)) if status != 'Open' else created_date
                )
                db.session.add(ticket)
                db.session.flush()
                
                # Classify ticket
                category, confidence = categorize_ticket_nlp(ticket.title, ticket.description)
                ticket_category = TicketCategory(
                    ticket_id=ticket.id,
                    category=category,
                    confidence=confidence
                )
                db.session.add(ticket_category)
            
            # Add more diverse tickets
            more_tickets = [
                # More network problems
                {'type': 'network', 'title': 'DNS Server problem', 'description': 'Cannot resolve domain names, websites do not open', 'priority': 'High', 'device': 'DNS Server', 'users': 45},
                {'type': 'network', 'title': 'DHCP problem', 'description': 'New devices do not get IP address automatically', 'priority': 'High', 'device': 'Main Switch', 'users': 20},
                {'type': 'network', 'title': 'VPN problem', 'description': 'Cannot connect to VPN server from outside office', 'priority': 'High', 'device': 'Firewall', 'users': 15},
                {'type': 'network', 'title': 'Bandwidth problem', 'description': 'Bandwidth consumption very high, network slow', 'priority': 'Medium', 'device': 'Main Router', 'users': 40},
                {'type': 'network', 'title': 'Firewall problem', 'description': 'Firewall blocking important connections', 'priority': 'High', 'device': 'Firewall', 'users': 25},
                
                # More hardware problems
                {'type': 'hardware', 'title': 'RAM problem', 'description': 'Device running very slowly, problem may be in memory', 'priority': 'High', 'device': 'Management Workstation', 'users': 1},
                {'type': 'hardware', 'title': 'CPU problem', 'description': 'Processor overheating excessively, device crashes', 'priority': 'Critical', 'device': 'Web Server', 'users': 0},
                {'type': 'hardware', 'title': 'Motherboard problem', 'description': 'Motherboard does not work, device does not start', 'priority': 'Critical', 'device': 'Sales Workstation', 'users': 1},
                {'type': 'hardware', 'title': 'Graphics Card problem', 'description': 'Graphics card does not work, screen is black', 'priority': 'High', 'device': 'Management Workstation', 'users': 1},
                {'type': 'hardware', 'title': 'Network Card problem', 'description': 'Network card does not work, no connection', 'priority': 'High', 'device': 'Sales Workstation', 'users': 1},
                {'type': 'hardware', 'title': 'USB Ports problem', 'description': 'USB ports do not work, cannot connect devices', 'priority': 'Medium', 'device': 'Management Workstation', 'users': 1},
                {'type': 'hardware', 'title': 'Sound Card problem', 'description': 'Sound card does not work, no sound', 'priority': 'Low', 'device': 'Sales Workstation', 'users': 1},
                
                # More software problems
                {'type': 'software', 'title': 'Windows Update problem', 'description': 'Windows updates fail to install', 'priority': 'Medium', 'device': 'Management Workstation', 'users': 1},
                {'type': 'software', 'title': 'Antivirus problem', 'description': 'Antivirus detects threats but cannot remove them', 'priority': 'High', 'device': 'Sales Workstation', 'users': 1},
                {'type': 'software', 'title': 'Office problem', 'description': 'Microsoft Office crashes when opening files', 'priority': 'High', 'device': 'Management Workstation', 'users': 3},
                {'type': 'software', 'title': 'Browser problem', 'description': 'Browser does not open websites, shows error', 'priority': 'Medium', 'device': 'Sales Workstation', 'users': 1},
                {'type': 'software', 'title': 'Email Client problem', 'description': 'Email client does not receive messages', 'priority': 'High', 'device': 'Management Workstation', 'users': 2},
                {'type': 'software', 'title': 'ERP System problem', 'description': 'ERP system does not work, database disconnected', 'priority': 'Critical', 'device': 'Main Database Server', 'users': 50},
                {'type': 'software', 'title': 'Backup Software problem', 'description': 'Backup software does not work', 'priority': 'High', 'device': 'Main Database Server', 'users': 0},
                {'type': 'software', 'title': 'Web Server problem', 'description': 'Web server does not respond, site unavailable', 'priority': 'Critical', 'device': 'Web Server', 'users': 100},
                {'type': 'software', 'title': 'Mail Server problem', 'description': 'Mail server does not work, cannot send messages', 'priority': 'Critical', 'device': 'Email Server', 'users': 60},
                {'type': 'software', 'title': 'Database Connection problem', 'description': 'Database connection failed, applications do not work', 'priority': 'Critical', 'device': 'Main Database Server', 'users': 45},
                
                # More printer problems
                {'type': 'printer', 'title': 'Printer Driver problem', 'description': 'Printer driver does not work, cannot print', 'priority': 'High', 'device': 'Main Office Printer', 'users': 10},
                {'type': 'printer', 'title': 'Printer Queue problem', 'description': 'Print queue is full, printer does not print', 'priority': 'Medium', 'device': 'Technical Department Printer', 'users': 5},
                {'type': 'printer', 'title': 'Printer Settings problem', 'description': 'Printer settings do not save, revert to defaults', 'priority': 'Low', 'device': 'Management Printer', 'users': 2},
                
                # Other problems
                {'type': 'other', 'title': 'Security problem', 'description': 'Hacking attempt detected, needs immediate inspection', 'priority': 'Critical', 'device': 'Firewall', 'users': 0},
                {'type': 'other', 'title': 'Monitoring problem', 'description': 'Monitoring system does not work, cannot track devices', 'priority': 'High', 'device': 'Monitoring Server', 'users': 0},
                {'type': 'other', 'title': 'License problem', 'description': 'Software license expired, needs renewal', 'priority': 'Medium', 'device': 'Management Workstation', 'users': 1},
                {'type': 'other', 'title': 'Access Control problem', 'description': 'Access control system does not work', 'priority': 'High', 'device': 'Control Server', 'users': 0},
            ]
            
            tickets_data.extend(more_tickets)
            
            # Create additional random diverse tickets
            network_titles = [
                'Slow website loading', 'Internet connection outage', 'WiFi problem',
                'LAN problem', 'WAN problem', 'Switch problem',
                'Router problem', 'Access Point problem', 'Network Cable problem',
                'Port problem', 'VLAN problem', 'Subnet problem'
            ]
            
            hardware_titles = [
                'Screen problem', 'Keyboard problem', 'Mouse problem',
                'Power problem', 'Fan problem', 'Hard drive problem',
                'RAM problem', 'CPU problem', 'Motherboard problem',
                'Graphics Card problem', 'Network Card problem', 'Sound Card problem'
            ]
            
            software_titles = [
                'System slowness', 'Application problem', 'Update problem',
                'Virus problem', 'Database problem', 'Email problem',
                'Windows problem', 'Office problem', 'Browser problem',
                'ERP problem', 'Backup problem', 'Web Server problem'
            ]
            
            printer_titles = [
                'Printing problem', 'Printer not working', 'Ink problem',
                'Paper problem', 'Driver problem', 'Settings problem'
            ]
            
            network_descriptions = [
                'Network very slow', 'Internet connection disconnected', 'WiFi unstable',
                'Local network does not work', 'Connection between devices failed', 'Switch does not work',
                'Router disabled', 'Access point does not work', 'Network cable damaged',
                'Port does not work', 'VLAN not configured', 'Subnet incorrect'
            ]
            
            hardware_descriptions = [
                'Screen does not work', 'Keyboard damaged', 'Mouse does not respond',
                'Power supply disabled', 'Fan does not work', 'Hard drive damaged',
                'Memory damaged', 'Processor overheating', 'Motherboard disabled',
                'Graphics card does not work', 'Network card disabled', 'Sound card damaged'
            ]
            
            software_descriptions = [
                'System very slow', 'Application crashes', 'Updates fail',
                'Viruses spreading', 'Database disabled', 'Email does not work',
                'Windows does not start', 'Office crashes', 'Browser does not open websites',
                'ERP system disabled', 'Backup failed', 'Web server does not work'
            ]
            
            printer_descriptions = [
                'Printer does not print', 'Printer disabled', 'Ink low',
                'Paper stuck', 'Driver does not work', 'Settings incorrect'
            ]
            
            type_titles_map = {
                'network': network_titles,
                'hardware': hardware_titles,
                'software': software_titles,
                'printer': printer_titles,
                'other': network_titles + hardware_titles + software_titles
            }
            
            type_descriptions_map = {
                'network': network_descriptions,
                'hardware': hardware_descriptions,
                'software': software_descriptions,
                'printer': printer_descriptions,
                'other': network_descriptions + hardware_descriptions + software_descriptions
            }
            
            for i in range(100 - len(tickets_data)):
                created_date = datetime.utcnow() - timedelta(days=random.randint(0, 30))
                status = random.choice(statuses)
                priority = random.choice(priorities)
                ticket_type = random.choice(ticket_types)
                
                # Choose appropriate title and description based on type
                titles = type_titles_map.get(ticket_type, network_titles)
                descriptions = type_descriptions_map.get(ticket_type, network_descriptions)
                
                title = random.choice(titles)
                description = random.choice(descriptions)
                
                printer_id = None
                device_name = None
                affected_users = 1
                
                if ticket_type == 'printer' and printer_ids:
                    printer_id = random.choice(printer_ids)
                    printer = Printer.query.get(printer_id)
                    device_name = printer.name if printer else None
                    affected_users = random.randint(1, 10)
                elif device_ids:
                    device = Device.query.get(random.choice(device_ids))
                    device_name = device.name if device else None
                    # Determine number of users based on device type
                    if device and device.device_type == 'server':
                        affected_users = random.randint(20, 100)
                    elif device and device.device_type == 'network_device':
                        affected_users = random.randint(10, 50)
                    else:
                        affected_users = random.randint(1, 5)
                
                ticket = Ticket(
                    printer_id=printer_id,
                    ticket_type=ticket_type,
                    device_name=device_name,
                    affected_users_count=affected_users,
                    reporter_email=random.choice(emails),
                    title=title,
                    description=description,
                    priority=priority,
                    status=status,
                    created_at=created_date,
                    updated_at=created_date + timedelta(hours=random.randint(1, 72)) if status != 'Open' else created_date
                )
                db.session.add(ticket)
                db.session.flush()
                
                # Classify ticket
                category, confidence = categorize_ticket_nlp(ticket.title, ticket.description)
                ticket_category = TicketCategory(
                    ticket_id=ticket.id,
                    category=category,
                    confidence=confidence
                )
                db.session.add(ticket_category)
            
            db.session.commit()
        
        # Add default alert data
        if Alert.query.count() == 0:
            printers = Printer.query.all()
            tickets = Ticket.query.filter_by(priority='High').limit(5).all()
            
            # Low ink level alerts
            for printer in printers:
                if printer.ink_level < 20:
                    alert = Alert(
                        printer_id=printer.id,
                        alert_type='low_ink',
                        message=f'Low ink level in {printer.name} ({printer.ink_level}%)',
                        severity='high' if printer.ink_level < 10 else 'medium',
                        is_read=False
                    )
                    db.session.add(alert)
            
            # Offline printer alerts
            for printer in printers:
                if printer.status == 'offline':
                    alert = Alert(
                        printer_id=printer.id,
                        alert_type='offline',
                        message=f'Printer {printer.name} is offline',
                        severity='high',
                        is_read=False
                    )
                    db.session.add(alert)
            
            # High priority ticket alerts
            for ticket in tickets:
                alert = Alert(
                    ticket_id=ticket.id,
                    alert_type='high_priority',
                    message=f'High priority ticket: {ticket.title}',
                    severity='critical',
                    is_read=False
                )
                db.session.add(alert)
            
            db.session.commit()
        
        # Add default maintenance schedule data
        if MaintenanceSchedule.query.count() == 0:
            printers = Printer.query.all()
            maintenance_types = ['cleaning', 'inspection', 'repair', 'replacement']
            
            for i, printer in enumerate(printers[:8]):  # Schedule maintenance for 8 printers
                schedule_date = datetime.utcnow() + timedelta(days=random.randint(1, 30))
                maintenance_type = random.choice(maintenance_types)
                
                schedule = MaintenanceSchedule(
                    printer_id=printer.id,
                    maintenance_type=maintenance_type,
                    scheduled_date=schedule_date,
                    status='scheduled',
                    notes=f'Scheduled maintenance for {printer.name}'
                )
                db.session.add(schedule)
            
            db.session.commit()
        
        # Add default ink depletion prediction data
        if InkPrediction.query.count() == 0:
            printers = Printer.query.all()
            
            for printer in printers:
                predicted_date, confidence = predict_ink_depletion(printer.id, printer.ink_level)
                if predicted_date:
                    prediction = InkPrediction(
                        printer_id=printer.id,
                        current_level=printer.ink_level,
                        predicted_depletion_date=predicted_date,
                        confidence_score=confidence
                    )
                    db.session.add(prediction)
            
            db.session.commit()

# ========== AI and Natural Language Processing Functions ==========

def generate_ai_response(title, description, category, ticket_type='printer'):
    # Use trained model if available
    if AI_MODEL_AVAILABLE and ai_model and ai_model.is_trained:
        try:
            response = ai_model.generate_response(title, description, category)
            return response
        except Exception as e:
            print(f"Error using trained model: {e}")
            # Fallback to backup system
    
    # Backup system (knowledge base)
    text = (title or '') + ' ' + (description or '')
    text_lower = text.lower()
    
    # Knowledge base for common solutions by category
    solutions_db = {
        'network': {
            'keywords': ['connection', 'network', 'wifi', 'lan', 'ip', 'cable'],
            'steps': [
                '1. Check network cable connection',
                '2. Restart the router',
                '3. Check IP and DNS settings',
                '4. Test connection using ping',
                '5. Check firewall settings'
            ],
            'solutions': [
                'Restart router',
                'Check network settings',
                'Reset TCP/IP settings',
                'Check network cable'
            ],
            'guidance': 'If the problem persists after trying the above steps, please contact the technical support team with details of the steps you tried.'
        },
        'hardware': {
            'keywords': ['device', 'mechanical', 'failure', 'noise', 'paper', 'drive'],
            'steps': [
                '1. Check device power connection',
                '2. Restart the device',
                '3. Check for any visible errors',
                '4. Check cables and connections',
                '5. Review device user manual'
            ],
            'solutions': [
                'Restart device',
                'Check cables and connections',
                'Clean device from dust',
                'Check device warranty'
            ],
            'guidance': 'If the device still does not work correctly, you may need technical maintenance. Please contact support team.'
        },
        'software': {
            'keywords': ['program', 'application', 'system', 'driver', 'install', 'software'],
            'steps': [
                '1. Restart the application',
                '2. Check for available updates',
                '3. Reinstall the application',
                '4. Check system requirements',
                '5. Review error log'
            ],
            'solutions': [
                'Reinstall application',
                'Update application to latest version',
                'Check system requirements',
                'Run application as Administrator'
            ],
            'guidance': 'If the problem persists, you may need to update the system or reinstall the software. Please contact support team.'
        },
        'printer': {
            'keywords': ['printer', 'print', 'ink', 'paper'],
            'steps': [
                '1. Check printer network connection',
                '2. Check ink and paper levels',
                '3. Restart the printer',
                '4. Check print queue',
                '5. Reinstall printer driver'
            ],
            'solutions': [
                'Restart printer',
                'Check ink and paper levels',
                'Clear print queue',
                'Reinstall printer driver'
            ],
            'guidance': 'If the problem persists, please check printer status in control panel and contact support team.'
        }
    }
    
    # Determine appropriate category
    matched_category = category
    if matched_category not in solutions_db:
        matched_category = 'hardware'  # default
    
    solution_data = solutions_db.get(matched_category, solutions_db['hardware'])
    
    # Build initial response
    initial_response = f"""
    Thank you for contacting us. Based on the problem description, this appears to be a {matched_category} related issue.
    
    Please try the following steps before contacting the support team:
    """
    
    troubleshooting_steps = '\n'.join(solution_data['steps'])
    common_solutions = '\n'.join([f"• {sol}" for sol in solution_data['solutions']])
    guidance = solution_data['guidance']
    
    # Calculate confidence score based on keyword matching
    confidence = 0.7
    matched_keywords = sum(1 for kw in solution_data['keywords'] if kw in text_lower)
    if matched_keywords > 0:
        confidence = min(0.7 + (matched_keywords * 0.1), 0.95)
    
    return {
        'initial_response': initial_response.strip(),
        'troubleshooting_steps': troubleshooting_steps,
        'common_solutions': common_solutions,
        'guidance': guidance,
        'confidence': confidence
    }

def calculate_ai_priority(title, description, printer_status=None, ink_level=None, ticket_type='printer', affected_users=1, device_name=None):
    # Use trained model if available
    if AI_MODEL_AVAILABLE and ai_model and ai_model.is_trained:
        try:
            priority, score = ai_model.predict_priority(title + ' ' + description, affected_users, device_name)
            # Adjust based on printer status and ink level
            if printer_status == 'offline':
                score += 30
            if ink_level is not None and ink_level < 10:
                score += 25
            
            # Recalculate priority based on updated score
            if score >= 90:
                priority = 'Critical'
            elif score >= 70:
                priority = 'High'
            elif score >= 40:
                priority = 'Medium'
            else:
                priority = 'Low'
            
            return priority, min(score, 100)
        except Exception as e:
            print(f"Error using trained model for priority: {e}")
            # Fallback to backup system
    
    # Backup system (traditional algorithm)
    score = 0
    text = (title or '') + ' ' + (description or '')
    text_lower = text.lower()
    
    # Enhanced priority keywords with improved weights
    critical_priority_keywords = {
        'critical': 50, 'emergency': 45, 'down': 40, 'outage': 45, 'crash': 40,
        'security breach': 50, 'data loss': 50, 'system down': 45, 'complete failure': 45,
        'hack': 50, 'breach': 50, 'unauthorized access': 50, 'malware': 45, 'virus outbreak': 50
    }
    
    high_priority_keywords = {
        'urgent': 35, 'not working': 30, 'disabled': 30, 'stopped': 30, 'broken': 30,
        'error': 25, 'failed': 28, 'major problem': 32, 'immediate': 30, 'severe': 30,
        'cannot access': 30, 'unavailable': 28, 'corrupted': 30, 'damaged': 28,
        'database down': 40, 'server down': 40, 'network down': 35, 'service unavailable': 32
    }
    
    medium_priority_keywords = {
        'slow': 18, 'problem': 15, 'not responding': 20, 'unclear': 12, 'distorted': 15,
        'delay': 16, 'difficulty': 15, 'issue': 12, 'glitch': 10, 'minor': 8,
        'intermittent': 15, 'unstable': 18, 'degraded': 15, 'performance issue': 18
    }
    
    low_priority_keywords = {
        'improvement': 6, 'suggestion': 5, 'inquiry': 4, 'question': 4, 'query': 4,
        'enhancement': 5, 'optimization': 5, 'feature request': 4, 'cosmetic': 3
    }
    
    # Calculate score based on keywords found (check critical first)
    for keyword, weight in critical_priority_keywords.items():
        if keyword in text_lower:
            score += weight
    
    for keyword, weight in high_priority_keywords.items():
        if keyword in text_lower:
            score += weight
    
    for keyword, weight in medium_priority_keywords.items():
        if keyword in text_lower:
            score += weight
    
    for keyword, weight in low_priority_keywords.items():
        if keyword in text_lower:
            score += weight
    
    # Printer status impact
    if printer_status == 'offline':
        score += 30
    elif printer_status == 'online' and ink_level is not None:
        if ink_level < 10:
            score += 25
        elif ink_level < 20:
            score += 20
        elif ink_level < 50:
            score += 12
    
    # Ink level impact
    if ink_level is not None:
        if ink_level < 10:
            score += 25
        elif ink_level < 20:
            score += 18
        elif ink_level < 30:
            score += 12
    
    # Text length impact (detailed problems may be more important)
    text_length = len(text)
    if text_length > 200:
        score += 5
    elif text_length < 50:
        score -= 3
    
    # Enhanced affected users impact (more granular)
    if affected_users >= 100:
        score += 50  # Critical - affects entire organization
    elif affected_users >= 50:
        score += 40  # High - affects large group
    elif affected_users >= 20:
        score += 30  # High - affects department
    elif affected_users >= 10:
        score += 20  # Medium - affects team
    elif affected_users >= 5:
        score += 12  # Medium - affects small group
    elif affected_users >= 2:
        score += 5   # Low - affects few users
    
    # Enhanced device/system type impact
    if device_name:
        device_lower = device_name.lower()
        if any(keyword in device_lower for keyword in ['database server', 'main server', 'primary server']):
            score += 45  # Critical infrastructure
        elif any(keyword in device_lower for keyword in ['server', 'database']):
            score += 35  # Servers are critical
        elif any(keyword in device_lower for keyword in ['firewall', 'security']):
            score += 40  # Security devices are critical
        elif any(keyword in device_lower for keyword in ['router', 'main router', 'core router']):
            score += 30  # Core network devices
        elif any(keyword in device_lower for keyword in ['network', 'switch', 'access point']):
            score += 25  # Network devices are important
        elif any(keyword in device_lower for keyword in ['workstation', 'pc', 'laptop']):
            score += 8   # Individual workstations
        elif any(keyword in device_lower for keyword in ['printer']):
            score += 5   # Printers are relatively less important
    
    # Enhanced impact of previous similar failures (pattern detection)
    if title and description:
        # Search for similar tickets in last 30 days
        similar_tickets = Ticket.query.filter(
            Ticket.created_at >= datetime.utcnow() - timedelta(days=30),
            Ticket.title.contains(title[:20]) if len(title) > 20 else Ticket.title == title
        ).count()
        
        # Also check for similar descriptions
        similar_by_desc = Ticket.query.filter(
            Ticket.created_at >= datetime.utcnow() - timedelta(days=30),
            Ticket.description.contains(description[:30]) if len(description) > 30 else Ticket.description == description
        ).count()
        
        total_similar = max(similar_tickets, similar_by_desc)
        
        if total_similar >= 10:
            score += 40  # Critical recurring problem
        elif total_similar >= 5:
            score += 30  # High recurring problem
        elif total_similar >= 3:
            score += 20  # Medium recurring problem
        elif total_similar >= 2:
            score += 12  # Low recurring problem
    
    # Enhanced priority determination with better thresholds
    if score >= 95:
        return 'Critical', min(score, 100)
    elif score >= 75:
        return 'High', score
    elif score >= 45:
        return 'Medium', score
    elif score >= 20:
        return 'Low', score
    else:
        return 'Low', max(score, 10)

def categorize_ticket_nlp(title, description):
    # Use trained model if available
    if AI_MODEL_AVAILABLE and ai_model and ai_model.is_trained:
        try:
            category, confidence = ai_model.predict_category(title + ' ' + description)
            return category, confidence
        except Exception as e:
            print(f"Error using trained model for categorization: {e}")
            # Fallback to backup system
    
    # Backup system (traditional algorithm)
    text = (title or '') + ' ' + (description or '')
    text_lower = text.lower()
    
    # Enhanced keywords with better coverage for all IT problem types
    categories = {
        'hardware': {
            'keywords': ['device', 'mechanical', 'noise', 'drive', 'failure', 'screen', 'keyboard', 'mouse', 'hardware', 'cpu', 'ram', 'motherboard', 'hardware failure', 'physical', 'component', 'peripheral', 'monitor', 'display', 'graphics card', 'power supply', 'fan', 'heating', 'overheating'],
            'weights': [3, 2, 1, 2, 3, 3, 2, 2, 3, 3, 3, 3, 4, 2, 2, 2, 3, 3, 3, 3, 2, 2, 3]
        },
        'software': {
            'keywords': ['driver', 'program', 'application', 'system', 'install', 'settings', 'software', 'windows', 'linux', 'mac', 'app', 'update', 'os', 'operating system', 'crash', 'freeze', 'hang', 'bug', 'glitch', 'error message', 'blue screen', 'bsod', 'update failed', 'installation failed'],
            'weights': [3, 2, 3, 3, 2, 2, 3, 3, 2, 2, 2, 2, 3, 3, 3, 2, 2, 2, 2, 3, 3, 3, 3, 3]
        },
        'network': {
            'keywords': ['network', 'connection', 'ip', 'wifi', 'lan', 'cable', 'wire', 'wireless', 'router', 'switch', 'internet', 'dns', 'dhcp', 'vpn', 'firewall', 'bandwidth', 'latency', 'packet loss', 'timeout', 'disconnect', 'cannot connect', 'no internet', 'slow connection'],
            'weights': [4, 4, 3, 3, 3, 2, 2, 3, 3, 3, 3, 3, 3, 3, 3, 2, 2, 3, 3, 3, 3, 3, 3]
        },
        'printer': {
            'keywords': ['printer', 'print', 'printing', 'print job', 'print queue', 'print driver', 'cannot print', 'print error'],
            'weights': [4, 3, 3, 3, 3, 3, 4, 3]
        },
        'ink': {
            'keywords': ['ink', 'low ink', 'depleted', 'empty ink', 'low ink level', 'toner', 'cartridge', 'ink empty', 'out of ink', 'replace ink'],
            'weights': [3, 4, 3, 4, 4, 3, 3, 4, 4, 3]
        },
        'paper': {
            'keywords': ['paper', 'empty paper', 'paper jam', 'paper feed', 'stuck', 'jammed', 'out of paper', 'paper empty', 'paper stuck'],
            'weights': [3, 4, 4, 3, 3, 3, 4, 4, 3]
        },
        'other': {
            'keywords': [],
            'weights': []
        }
    }
    
    scores = {}
    for category, data in categories.items():
        if category == 'other':
            continue
        score = 0
        for i, keyword in enumerate(data['keywords']):
            if keyword in text_lower:
                weight = data['weights'][i] if i < len(data['weights']) else 1
                score += weight
        scores[category] = score
    
    if not any(scores.values()):
        return 'other', 0.5
    
    max_category = max(scores, key=scores.get)
    max_score = scores[max_category]
    total_possible = sum(categories[max_category]['weights'])
    confidence = min(max_score / total_possible if total_possible > 0 else 0.5, 1.0)
    
    return max_category, confidence

# ========== SNMP Monitoring Functions for Printers ==========

def get_printer_snmp_data(printer_ip, community='public', timeout=3):
    if not SNMP_AVAILABLE:
        return None
    
    try:
        # Common OIDs for printers
        oids = {
            'status': '1.3.6.1.2.1.25.3.2.1.5.1',  # Printer status
            'ink_level_black': '1.3.6.1.2.1.43.11.1.1.9.1.1',  # Black ink level
            'ink_level_cyan': '1.3.6.1.2.1.43.11.1.1.9.1.2',  # Cyan ink level
            'ink_level_magenta': '1.3.6.1.2.1.43.11.1.1.9.1.3',  # Magenta ink level
            'ink_level_yellow': '1.3.6.1.2.1.43.11.1.1.9.1.4',  # Yellow ink level
            'paper_status': '1.3.6.1.2.1.43.18.1.1.8.1.1',  # Paper status
            'error_status': '1.3.6.1.2.1.25.3.5.1.1.1'  # Error status
        }
        
        result = {}
        
        # Attempt to read printer status
        for name, oid in oids.items():
            try:
                iterator = getCmd(
                    SnmpEngine(),
                    CommunityData(community),
                    UdpTransportTarget((printer_ip, 161), timeout=timeout),
                    ContextData(),
                    ObjectType(ObjectIdentity(oid))
                )
                
                errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
                
                if errorIndication:
                    continue
                elif errorStatus:
                    continue
                else:
                    for varBind in varBinds:
                        result[name] = str(varBind[1])
            except:
                continue
        
        return result if result else None
    except Exception as e:
        print(f"Error reading SNMP from {printer_ip}: {e}")
        return None

def monitor_printer_snmp(printer_id, printer_ip, printer_name):
    if not printer_ip:
        return
    
    snmp_data = get_printer_snmp_data(printer_ip)
    
    if not snmp_data:
        # Printer not available via SNMP
        printer = Printer.query.get(printer_id)
        if printer and printer.status == 'online':
            printer.status = 'offline'
            printer.last_seen = datetime.utcnow()
            db.session.commit()
            
            # Create automatic ticket
            create_auto_ticket(
                ticket_type='printer',
                title=f'Printer {printer_name} is offline',
                description=f'Failed to connect to printer {printer_name} ({printer_ip}) via SNMP',
                priority='High',
                device_name=printer_name
            )
        return
    
    printer = Printer.query.get(printer_id)
    if not printer:
        return
    
    # Update printer status
    printer.status = 'online'
    printer.last_seen = datetime.utcnow()
    
    # Read ink level
    ink_levels = []
    for color in ['black', 'cyan', 'magenta', 'yellow']:
        key = f'ink_level_{color}'
        if key in snmp_data:
            try:
                level = int(snmp_data[key])
                ink_levels.append(level)
            except:
                pass
    
    if ink_levels:
        # Use lowest ink level
        min_ink = min(ink_levels)
        printer.ink_level = min_ink
        
        # Create alert or ticket if ink is low
        if min_ink < 10 and printer.ink_level >= 10:
            create_auto_ticket(
                ticket_type='printer',
                title=f'Low ink level in {printer_name}',
                description=f'Ink level in printer {printer_name} is very low ({min_ink}%)',
                priority='Medium',
                device_name=printer_name
            )
        elif min_ink < 5:
            create_auto_ticket(
                ticket_type='printer',
                title=f'Critical ink level in {printer_name}',
                description=f'Ink level in printer {printer_name} is critical ({min_ink}%) - needs immediate replacement',
                priority='Critical',
                device_name=printer_name
            )
        elif min_ink < 10:
            create_auto_ticket(
                ticket_type='printer',
                title=f'Very low ink level in {printer_name}',
                description=f'Ink level in printer {printer_name} is very low ({min_ink}%) - replacement needed soon',
                priority='High',
                device_name=printer_name
            )
    
    # Check paper status
    if 'paper_status' in snmp_data:
        paper_status = snmp_data['paper_status']
        if 'empty' in paper_status.lower() or 'low' in paper_status.lower():
            create_auto_ticket(
                ticket_type='printer',
                title=f'Paper low or empty in {printer_name}',
                description=f'Paper status in printer {printer_name}: {paper_status}',
                priority='Medium',
                device_name=printer_name
            )
    
    # Check for errors (enhanced)
    if 'error_status' in snmp_data:
        error_status = snmp_data['error_status']
        if error_status and error_status != '0' and 'ok' not in error_status.lower():
            # Determine priority based on error severity
            error_lower = error_status.lower()
            if any(severity in error_lower for severity in ['critical', 'fatal', 'severe', 'complete failure']):
                priority = 'Critical'
            elif any(severity in error_lower for severity in ['major', 'serious', 'hardware failure']):
                priority = 'High'
            else:
                priority = 'Medium'
            
            create_auto_ticket(
                ticket_type='printer',
                title=f'Error in {printer_name}',
                description=f'Error detected in printer {printer_name}: {error_status}',
                priority=priority,
                device_name=printer_name
            )
    
    db.session.commit()

def create_auto_ticket(ticket_type, title, description, priority='Medium', device_name=None):
    # Enhanced duplicate detection - check for similar open ticket in last 2 hours
    recent_ticket = Ticket.query.filter(
        Ticket.title == title,
        Ticket.status.in_(['Open', 'In Progress']),
        Ticket.created_at >= datetime.utcnow() - timedelta(hours=2)
    ).first()
    
    # Also check by description similarity for critical issues
    if not recent_ticket and priority in ['Critical', 'High']:
        similar_ticket = Ticket.query.filter(
            Ticket.description.contains(description[:50]) if len(description) > 50 else Ticket.description == description,
            Ticket.status.in_(['Open', 'In Progress']),
            Ticket.created_at >= datetime.utcnow() - timedelta(hours=1)
        ).first()
        if similar_ticket:
            recent_ticket = similar_ticket
    
    if recent_ticket:
        return  # Ticket already exists
    
    ticket = Ticket(
        ticket_type=ticket_type,
        title=title,
        description=description,
        priority=priority,
        status='Open',
        device_name=device_name,
        reporter_email='system@helpdesk.local'
    )
    
    db.session.add(ticket)
    db.session.flush()
    
    # Classify ticket
    category, confidence = categorize_ticket_nlp(title, description)
    ticket_category = TicketCategory(
        ticket_id=ticket.id,
        category=category,
        confidence=confidence
    )
    db.session.add(ticket_category)
    
    # Create alert
    alert = Alert(
        ticket_id=ticket.id,
        alert_type='auto_generated',
        message=f'Auto-generated ticket: {title}',
        severity='high' if priority in ['High', 'Critical'] else 'medium'
    )
    db.session.add(alert)
    
    db.session.commit()
    return ticket

def snmp_monitoring_worker():
    while True:
        try:
            printers = Printer.query.filter(Printer.ip_address.isnot(None)).all()
            for printer in printers:
                try:
                    monitor_printer_snmp(printer.id, printer.ip_address, printer.name)
                except Exception as e:
                    print(f"Error monitoring printer {printer.name}: {e}")
            
            # Wait 5 minutes before next monitoring
            time.sleep(300)
        except Exception as e:
            print(f"Error in SNMP monitoring worker: {e}")
            time.sleep(60)  # Wait one minute on error

def detect_patterns(printer_id):
    # Advanced algorithm for analyzing patterns and recurring problems
    tickets = Ticket.query.filter_by(printer_id=printer_id).all()
    
    if len(tickets) < 3:
        return None
    
    # Analyze recurring problems with percentage calculation
    categories = {}
    priorities = {'High': 0, 'Medium': 0, 'Low': 0}
    statuses = {'Open': 0, 'In Progress': 0, 'Resolved': 0}
    
    for ticket in tickets:
        category, _ = categorize_ticket_nlp(ticket.title, ticket.description)
        categories[category] = categories.get(category, 0) + 1
        priorities[ticket.priority] = priorities.get(ticket.priority, 0) + 1
        statuses[ticket.status] = statuses.get(ticket.status, 0) + 1
    
    most_common = max(categories, key=categories.get) if categories else None
    
    # Calculate percentages
    total = len(tickets)
    category_percentages = {k: round((v / total) * 100, 1) for k, v in categories.items()}
    priority_percentages = {k: round((v / total) * 100, 1) for k, v in priorities.items()}
    
    return {
        'total_tickets': total,
        'most_common_issue': most_common,
        'issue_frequency': categories,
        'issue_percentages': category_percentages,
        'priority_distribution': priority_percentages,
        'status_distribution': {k: round((v / total) * 100, 1) for k, v in statuses.items()}
    }

def generate_smart_alert(printer_id=None, ticket_id=None):
    # Smart algorithm for creating automatic alerts
    alerts = []
    
    if printer_id:
        printer = Printer.query.get(printer_id)
        if printer:
            # Low ink level alert with different levels
            if printer.ink_level < 20:
                if printer.ink_level < 5:
                    severity = 'critical'
                elif printer.ink_level < 10:
                    severity = 'high'
                else:
                    severity = 'medium'
                
                alerts.append(Alert(
                    printer_id=printer_id,
                    alert_type='low_ink',
                    message=f'Low ink level in {printer.name} ({printer.ink_level}%)',
                    severity=severity
                ))
            
            # Offline printer alert
            if printer.status == 'offline':
                # Calculate offline duration
                if printer.last_seen:
                    offline_duration = (datetime.utcnow() - printer.last_seen).total_seconds() / 3600
                    if offline_duration > 24:
                        severity = 'critical'
                    elif offline_duration > 12:
                        severity = 'high'
                    else:
                        severity = 'medium'
                else:
                    severity = 'high'
                
                alerts.append(Alert(
                    printer_id=printer_id,
                    alert_type='offline',
                    message=f'Printer {printer.name} is offline',
                    severity=severity
                ))
    
    if ticket_id:
        ticket = Ticket.query.get(ticket_id)
        if ticket:
            # Alerts for tickets by priority
            if ticket.priority == 'High':
                alerts.append(Alert(
                    ticket_id=ticket_id,
                    alert_type='high_priority',
                    message=f'High priority ticket: {ticket.title}',
                    severity='critical'
                ))
            elif ticket.priority == 'Medium' and ticket.status == 'Open':
                # Alert for medium priority tickets open for more than 24 hours
                if ticket.created_at:
                    hours_open = (datetime.utcnow() - ticket.created_at).total_seconds() / 3600
                    if hours_open > 24:
                        alerts.append(Alert(
                            ticket_id=ticket_id,
                            alert_type='stale_ticket',
                            message=f'Ticket open for more than 24 hours: {ticket.title}',
                            severity='medium'
                        ))
    
    for alert in alerts:
        db.session.add(alert)
    
    if alerts:
        db.session.commit()
    
    return alerts

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return home_redirect()
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = get_user_role(user)
            session['email'] = user.email or ''
            return home_redirect()
        else:
            return render_template('login.html', error='Invalid username or password')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@staff_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/portal')
@login_required
def employee_portal():
    if session.get('role') != 'employee':
        return redirect(url_for('dashboard'))
    return render_template('employee_portal.html')

@app.route('/portal/ticket/<int:ticket_id>')
@login_required
def employee_ticket_view(ticket_id):
    if session.get('role') != 'employee':
        return redirect(url_for('ticket_view', ticket_id=ticket_id))
    ticket = Ticket.query.get_or_404(ticket_id)
    if not user_can_access_ticket(ticket):
        return redirect(url_for('employee_portal'))
    printer = Printer.query.get(ticket.printer_id) if ticket.printer_id else None
    return render_template('employee_ticket.html', ticket=ticket, printer=printer)

@app.route('/printers', methods=['GET'])
@login_required
def get_printers():
    printers = Printer.query.all()
    if session.get('role') == 'employee':
        return jsonify([{'id': p.id, 'name': p.name, 'model': p.model} for p in printers])
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'ip_address': p.ip_address,
        'model': p.model,
        'status': p.status,
        'ink_level': p.ink_level,
        'last_seen': p.last_seen.isoformat() if p.last_seen else None
    } for p in printers])

@app.route('/devices', methods=['GET'])
@login_required
def get_devices():
    if session.get('role') == 'employee':
        return jsonify({'error': 'Access denied'}), 403
    devices = Device.query.all()
    return jsonify([{
        'id': d.id,
        'name': d.name,
        'device_type': d.device_type,
        'ip_address': d.ip_address,
        'location': d.location,
        'status': d.status,
        'last_seen': d.last_seen.isoformat() if d.last_seen else None
    } for d in devices])

@app.route('/tickets', methods=['GET'])
@login_required
def get_tickets():
    status_filter = request.args.get('status')
    priority_filter = request.args.get('priority')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    
    query = Ticket.query

    if session.get('role') == 'employee':
        query = query.filter_by(created_by_user_id=session.get('user_id'))
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    if priority_filter:
        query = query.filter_by(priority=priority_filter)
    ticket_type_filter = request.args.get('ticket_type')
    if ticket_type_filter:
        query = query.filter_by(ticket_type=ticket_type_filter)
    
    # Calculate total tickets
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * per_page
    tickets = query.order_by(Ticket.created_at.desc()).offset(offset).limit(per_page).all()
    
    result = []
    for t in tickets:
        printer = Printer.query.get(t.printer_id) if t.printer_id else None
        # Get AI response if available
        ai_response = AIResponse.query.filter_by(ticket_id=t.id).first()
        result.append({
            'id': t.id,
            'printer_id': t.printer_id,
            'printer_name': printer.name if printer else None,
            'ticket_type': t.ticket_type if hasattr(t, 'ticket_type') else 'printer',
            'device_name': t.device_name if hasattr(t, 'device_name') else None,
            'affected_users_count': t.affected_users_count if hasattr(t, 'affected_users_count') else 1,
            'reporter_email': t.reporter_email,
            'title': t.title,
            'description': t.description,
            'priority': t.priority,
            'status': t.status,
            'created_at': t.created_at.isoformat() if t.created_at else None,
            'updated_at': t.updated_at.isoformat() if t.updated_at else None,
            'has_ai_response': ai_response is not None
        })
    
    return jsonify({
        'tickets': result,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page,
        'has_more': offset + per_page < total
    })

@app.route('/tickets', methods=['POST'])
@login_required
def create_ticket():
    data = request.get_json() if request.is_json else request.form
    
    # Use AI to determine priority and categorization
    printer = Printer.query.get(data.get('printer_id')) if data.get('printer_id') else None
    printer_status = printer.status if printer else None
    ink_level = printer.ink_level if printer else None
    
    # Determine ticket type (system generalization)
    ticket_type = data.get('ticket_type', 'printer')
    device_name = data.get('device_name', printer.name if printer else None)
    affected_users = int(data.get('affected_users_count', 1))
    
    # Calculate priority using AI (enhanced)
    ai_priority, ai_score = calculate_ai_priority(
        data.get('title'),
        data.get('description'),
        printer_status,
        ink_level,
        ticket_type,
        affected_users,
        device_name
    )
    
    # Use priority specified by user or AI
    priority = data.get('priority', ai_priority)
    
    ticket = Ticket(
        printer_id=data.get('printer_id'),
        ticket_type=ticket_type,
        device_name=device_name,
        affected_users_count=affected_users,
        reporter_email=data.get('reporter_email') or session.get('email') or None,
        created_by_user_id=session.get('user_id'),
        title=data.get('title'),
        description=data.get('description'),
        priority=priority
    )
    
    db.session.add(ticket)
    db.session.flush()
    
    # Classify ticket using NLP
    category, confidence = categorize_ticket_nlp(ticket.title, ticket.description)
    ticket_category = TicketCategory(
        ticket_id=ticket.id,
        category=category,
        confidence=confidence
    )
    db.session.add(ticket_category)
    
    # Generate automatic initial response using AI
    ai_response_data = generate_ai_response(
        ticket.title,
        ticket.description,
        category,
        ticket_type
    )
    
    ai_response = AIResponse(
        ticket_id=ticket.id,
        initial_response=ai_response_data['initial_response'],
        troubleshooting_steps=ai_response_data['troubleshooting_steps'],
        common_solutions=ai_response_data['common_solutions'],
        guidance=ai_response_data['guidance'],
        confidence_score=ai_response_data['confidence']
    )
    db.session.add(ai_response)
    
    # Create smart alerts
    generate_smart_alert(ticket_id=ticket.id)
    
    db.session.commit()
    
    return jsonify({
        'id': ticket.id,
        'message': 'Ticket created successfully',
        'ai_priority': ai_priority,
        'ai_score': ai_score,
        'category': category,
        'confidence': confidence,
        'ai_response': {
            'initial_response': ai_response_data['initial_response'],
            'troubleshooting_steps': ai_response_data['troubleshooting_steps'],
            'common_solutions': ai_response_data['common_solutions'],
            'guidance': ai_response_data['guidance']
        }
    }), 201

@app.route('/ticket/<int:ticket_id>')
@login_required
def ticket_view(ticket_id):
    if session.get('role') == 'employee':
        return redirect(url_for('employee_ticket_view', ticket_id=ticket_id))
    
    ticket = Ticket.query.get_or_404(ticket_id)
    comments = TicketComment.query.filter_by(ticket_id=ticket_id).order_by(TicketComment.created_at).all()
    printer = Printer.query.get(ticket.printer_id) if ticket.printer_id else None
    
    return render_template('ticket_view.html', ticket=ticket, comments=comments, printer=printer, is_staff=True)

@app.route('/ticket/<int:ticket_id>/comment', methods=['POST'])
@staff_required
def add_comment(ticket_id):
    
    data = request.get_json() if request.is_json else request.form
    
    comment = TicketComment(
        ticket_id=ticket_id,
        author=session.get('username', 'Support Staff'),
        message=data.get('message')
    )
    
    db.session.add(comment)
    
    ticket = Ticket.query.get(ticket_id)
    if ticket:
        ticket.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        'id': comment.id,
        'message': 'Comment added successfully'
    }), 201

@app.route('/ticket/<int:ticket_id>/status', methods=['POST'])
@staff_required
def update_ticket_status(ticket_id):
    
    data = request.get_json() if request.is_json else request.form
    new_status = data.get('status')
    
    if new_status not in ['Open', 'In Progress', 'Resolved']:
        return jsonify({'error': 'Invalid status'}), 400
    
    ticket = Ticket.query.get_or_404(ticket_id)
    ticket.status = new_status
    ticket.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        'id': ticket.id,
        'status': ticket.status,
        'message': 'Status updated successfully'
    })

# API endpoint to get available ticket types
@app.route('/ticket-types', methods=['GET'])
def get_ticket_types():
    return jsonify({
        'ticket_types': [
            {'value': 'printer', 'label': 'Printer Problems'},
            {'value': 'network', 'label': 'Network Problems'},
            {'value': 'hardware', 'label': 'Hardware Problems'},
            {'value': 'software', 'label': 'Software & System Problems'},
            {'value': 'other', 'label': 'Other'}
        ]
    })

# API endpoint to train model
@app.route('/ai/train', methods=['POST'])
@admin_required
def train_ai_endpoint():
    
    try:
        from train_model import train_ai_model
        import threading
        
        # Run training in separate thread
        def train_in_background():
            with app.app_context():
                train_ai_model(epochs=50)
        
        thread = threading.Thread(target=train_in_background, daemon=True)
        thread.start()
        
        return jsonify({
            'message': 'Model training started in background',
            'status': 'training'
        })
    except Exception as e:
        return jsonify({'error': f'Error starting training: {str(e)}'}), 500

# API endpoint for model status
@app.route('/ai/status', methods=['GET'])
def ai_model_status():
    return jsonify({
        'is_trained': AI_MODEL_AVAILABLE and ai_model and ai_model.is_trained if ai_model else False,
        'model_available': AI_MODEL_AVAILABLE,
        'message': 'Model is ready' if (AI_MODEL_AVAILABLE and ai_model and ai_model.is_trained) else 'Model not trained - please run train_model.py'
    })

@app.route('/alerts', methods=['GET'])
@staff_required
def get_alerts():
    unread_only = request.args.get('unread_only', 'false').lower() == 'true'
    
    query = Alert.query
    if unread_only:
        query = query.filter_by(is_read=False)
    
    alerts = query.order_by(Alert.created_at.desc()).limit(50).all()
    
    return jsonify([{
        'id': a.id,
        'printer_id': a.printer_id,
        'ticket_id': a.ticket_id,
        'alert_type': a.alert_type,
        'message': a.message,
        'severity': a.severity,
        'is_read': a.is_read,
        'created_at': a.created_at.isoformat() if a.created_at else None
    } for a in alerts])

@app.route('/alerts/<int:alert_id>/read', methods=['POST'])
@staff_required
def mark_alert_read(alert_id):
    alert = Alert.query.get_or_404(alert_id)
    alert.is_read = True
    db.session.commit()
    return jsonify({'message': 'Alert marked as read'})

@app.route('/predictions/ink', methods=['GET'])
@staff_required
def get_ink_predictions():
    printers = Printer.query.all()
    predictions = []
    
    for printer in printers:
        predicted_date, confidence = predict_ink_depletion(printer.id, printer.ink_level)
        if predicted_date:
            predictions.append({
                'printer_id': printer.id,
                'printer_name': printer.name,
                'current_level': printer.ink_level,
                'predicted_depletion_date': predicted_date.isoformat(),
                'confidence': round(confidence, 2),
                'days_until_depletion': (predicted_date - datetime.utcnow()).days
            })
    
    return jsonify(predictions)

@app.route('/maintenance/schedule', methods=['GET'])
@staff_required
def get_maintenance_schedule():
    upcoming = request.args.get('upcoming', 'false').lower() == 'true'
    
    query = MaintenanceSchedule.query
    if upcoming:
        query = query.filter(MaintenanceSchedule.scheduled_date >= datetime.utcnow())
        query = query.filter_by(status='scheduled')
    
    schedules = query.order_by(MaintenanceSchedule.scheduled_date).all()
    
    return jsonify([{
        'id': m.id,
        'printer_id': m.printer_id,
        'maintenance_type': m.maintenance_type,
        'scheduled_date': m.scheduled_date.isoformat() if m.scheduled_date else None,
        'completed_date': m.completed_date.isoformat() if m.completed_date else None,
        'status': m.status,
        'notes': m.notes
    } for m in schedules])

@app.route('/maintenance/schedule', methods=['POST'])
@staff_required
def create_maintenance_schedule():
    data = request.get_json() if request.is_json else request.form
    
    schedule = MaintenanceSchedule(
        printer_id=data.get('printer_id'),
        maintenance_type=data.get('maintenance_type'),
        scheduled_date=datetime.fromisoformat(data.get('scheduled_date')),
        notes=data.get('notes')
    )
    
    db.session.add(schedule)
    db.session.commit()
    
    return jsonify({
        'id': schedule.id,
        'message': 'Maintenance scheduled successfully'
    }), 201

@app.route('/analytics/patterns/<int:printer_id>', methods=['GET'])
@staff_required
def get_printer_patterns(printer_id):
    patterns = detect_patterns(printer_id)
    return jsonify(patterns if patterns else {'message': 'Not enough data for analysis'})

@app.route('/analytics/ai-priority', methods=['POST'])
@login_required
def calculate_priority():
    data = request.get_json()
    title = data.get('title', '')
    description = data.get('description', '')
    printer_id = data.get('printer_id')
    ticket_type = data.get('ticket_type', 'printer')
    affected_users = int(data.get('affected_users_count', 1))
    device_name = data.get('device_name')
    
    printer = Printer.query.get(printer_id) if printer_id else None
    printer_status = printer.status if printer else None
    ink_level = printer.ink_level if printer else None
    
    priority, score = calculate_ai_priority(
        title, description, printer_status, ink_level,
        ticket_type, affected_users, device_name
    )
    category, confidence = categorize_ticket_nlp(title, description)
    
    # Generate preview of initial response
    ai_response_preview = generate_ai_response(title, description, category, ticket_type)
    
    return jsonify({
        'priority': priority,
        'score': score,
        'category': category,
        'confidence': confidence,
        'ai_response_preview': ai_response_preview['initial_response'][:200] + '...' if len(ai_response_preview['initial_response']) > 200 else ai_response_preview['initial_response']
    })

# API endpoint to get AI response for ticket
@app.route('/ticket/<int:ticket_id>/ai-response', methods=['GET'])
@login_required
def get_ai_response(ticket_id):
    ticket = Ticket.query.get_or_404(ticket_id)
    if not user_can_access_ticket(ticket):
        return jsonify({'error': 'Access denied'}), 403
    ai_response = AIResponse.query.filter_by(ticket_id=ticket_id).first()
    if not ai_response:
        return jsonify({'error': 'No AI response for this ticket'}), 404
    
    return jsonify({
        'id': ai_response.id,
        'initial_response': ai_response.initial_response,
        'troubleshooting_steps': ai_response.troubleshooting_steps,
        'common_solutions': ai_response.common_solutions,
        'guidance': ai_response.guidance,
        'confidence': ai_response.confidence_score,
        'created_at': ai_response.created_at.isoformat() if ai_response.created_at else None
    })

# API endpoint for manual SNMP monitoring
@app.route('/printers/<int:printer_id>/monitor', methods=['POST'])
@staff_required
def monitor_printer(printer_id):
    printer = Printer.query.get_or_404(printer_id)
    if not printer.ip_address:
        return jsonify({'error': 'Printer does not have an IP address'}), 400
    
    monitor_printer_snmp(printer.id, printer.ip_address, printer.name)
    
    return jsonify({
        'message': 'Printer monitored successfully',
        'printer_status': printer.status,
        'ink_level': printer.ink_level
    })

@app.route('/assets/<path:filename>')
def assets(filename):
    return send_from_directory(os.path.join(BASE_DIR, 'assets'), filename)

if __name__ == '__main__':
    # Update database first
    try:
        from migrate_db import migrate_database
        print("Updating database...")
        migrate_database()
    except Exception as e:
        print(f"Warning: Error updating database: {e}")
    
    init_db()
    
    # Start SNMP monitoring worker in separate thread
    if SNMP_AVAILABLE:
        snmp_thread = threading.Thread(target=snmp_monitoring_worker, daemon=True)
        snmp_thread.start()
        print("SNMP monitoring for printers started")
    else:
        print("SNMP monitoring disabled (library not available)")
    
    app.run(debug=True, host='127.0.0.1', port=5000)

