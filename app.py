from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import re
from decimal import Decimal, InvalidOperation

app = Flask(__name__)
CORS(app)

# Configure database using environment variables
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@localhost:5432/postgres'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class ValidationError(Exception):
    pass

class DatabaseError(Exception):
    pass

class ResourceNotFoundError(Exception):
    pass

def validate_string_field(value, field_name, max_length):
    if not value or not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a non-empty string")
    if len(value) > max_length:
        raise ValidationError(f"{field_name} must not exceed {max_length} characters")
    return value

def validate_email(email):
    email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    if not email_pattern.match(email):
        raise ValidationError("Invalid email format")
    return email

def validate_amount(amount):
    try:
        amount = Decimal(str(amount))
        if amount < Decimal('0'):
            raise ValidationError("Amount must be non-negative")
        return amount
    except (TypeError, ValueError, InvalidOperation):
        raise ValidationError("Amount must be a valid number")

def validate_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError("Invalid date format. Use YYYY-MM-DD")

def validate_date_range(start_date, end_date):
    if start_date >= end_date:
        raise ValidationError("End date must be after start date")

def validate_status(status):
    valid_statuses = ['Pending', 'Approved', 'Rejected']
    if status not in valid_statuses:
        raise ValidationError(f"Status must be one of: {', '.join(valid_statuses)}")
    return status

class Policyholder(db.Model):
    _tablename_ = 'policyholder'
    policyholder_id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact_info = db.Column(db.String(255), nullable=False)
    policies = db.relationship('Policy', backref='policyholder', lazy=True, cascade="all, delete-orphan")

    @staticmethod
    def validate_input(data):
        required_fields = ['policyholder_id', 'name', 'contact_info']
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"Missing required field: {field}")
        validate_string_field(data['policyholder_id'], 'Policyholder ID', 50)
        validate_string_field(data['name'], 'Name', 100)
        validate_email(data['contact_info'])
        return data

class Policy(db.Model):
    _tablename_ = 'policy'
    policy_id = db.Column(db.String(50), primary_key=True)
    policy_type = db.Column(db.String(100), nullable=False)
    coverage_amount = db.Column(db.Numeric(12, 2), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    policyholder_id = db.Column(db.String(50), db.ForeignKey('policyholder.policyholder_id'), nullable=False)
    claims = db.relationship('Claim', backref='policy', lazy=True, cascade="all, delete-orphan")

    @staticmethod
    def validate_input(data):
        required_fields = ['policy_id', 'policy_type', 'coverage_amount', 'start_date', 'end_date', 'policyholder_id']
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"Missing required field: {field}")
        validate_string_field(data['policy_id'], 'Policy ID', 50)
        validate_string_field(data['policy_type'], 'Policy Type', 100)
        validate_string_field(data['policyholder_id'], 'Policyholder ID', 50)
        data['coverage_amount'] = validate_amount(data['coverage_amount'])
        start_date = validate_date(data['start_date'])
        end_date = validate_date(data['end_date'])
        validate_date_range(start_date, end_date)
        return data

class Claim(db.Model):
    _tablename_ = 'claim'
    claim_id = db.Column(db.String(50), primary_key=True)
    description = db.Column(db.Text, nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Pending')
    policy_id = db.Column(db.String(50), db.ForeignKey('policy.policy_id'), nullable=False)

    @staticmethod
    def validate_input(data):
        required_fields = ['claim_id', 'description', 'amount', 'date', 'policy_id']
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"Missing required field: {field}")
        validate_string_field(data['claim_id'], 'Claim ID', 50)
        validate_string_field(data['description'], 'Description', 1000)
        validate_string_field(data['policy_id'], 'Policy ID', 50)
        data['amount'] = validate_amount(data['amount'])
        data['date'] = validate_date(data['date'])
        data['status'] = validate_status(data.get('status', 'Pending'))
        return data

@app.errorhandler(Exception)
def handle_error(error):
    if isinstance(error, ValidationError):
        return jsonify({"error": "Validation error", "message": str(error)}), 400
    elif isinstance(error, ResourceNotFoundError):
        return jsonify({"error": "Resource not found", "message": str(error)}), 404
    elif isinstance(error, DatabaseError):
        return jsonify({"error": "Database error", "message": str(error)}), 500
    else:
        return jsonify({"error": "Internal server error", "message": str(error)}), 500

def safe_commit():
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise DatabaseError(f"Database error: {str(e)}")

@app.route('/')
def home():
    return "Claims Management System API"

@app.route('/policyholders', methods=['POST'])
def create_policyholder():
    data = request.get_json()
    if not data:
        raise ValidationError("No input data provided")
    validated_data = Policyholder.validate_input(data)
    if Policyholder.query.get(validated_data['policyholder_id']):
        raise ValidationError("Policyholder ID already exists")
    ph = Policyholder(**validated_data)
    db.session.add(ph)
    safe_commit()
    return jsonify({
        'policyholder_id': ph.policyholder_id,
        'name': ph.name,
        'contact_info': ph.contact_info
    }), 201

@app.route('/policyholders/<policyholder_id>', methods=['GET'])
def get_policyholder(policyholder_id):
    ph = Policyholder.query.get(policyholder_id)
    if not ph:
        raise ResourceNotFoundError("Policyholder not found")
    return jsonify({
        'policyholder_id': ph.policyholder_id,
        'name': ph.name,
        'contact_info': ph.contact_info
    }), 200

@app.route('/policyholders/', methods=['GET'])
def get_all_policyholders():
    policyholders = Policyholder.query.all()
    return jsonify([{
        'policyholder_id': ph.policyholder_id,
        'name': ph.name,
        'contact_info': ph.contact_info
    } for ph in policyholders]), 200

@app.route('/policyholders/<policyholder_id>', methods=['PUT'])
def update_policyholder(policyholder_id):
    ph = Policyholder.query.get(policyholder_id)
    if not ph:
        raise ResourceNotFoundError("Policyholder not found")
    data = request.get_json()
    try:
        if 'name' in data:
            ph.name = validate_string_field(data['name'], 'Name', 100)
        if 'contact_info' in data:
            ph.contact_info = validate_email(data['contact_info'])
        safe_commit()
        return jsonify({
            'policyholder_id': ph.policyholder_id,
            'name': ph.name,
            'contact_info': ph.contact_info
        }), 200
    except Exception as e:
        db.session.rollback()
        raise e

@app.route('/policyholders/<policyholder_id>', methods=['DELETE'])
def delete_policyholder(policyholder_id):
    ph = Policyholder.query.get(policyholder_id)
    if not ph:
        raise ResourceNotFoundError("Policyholder not found")
    db.session.delete(ph)
    safe_commit()
    return jsonify({"message": "Policyholder deleted successfully"}), 200

@app.route('/policies', methods=['POST'])
def create_policy():
    data = request.get_json()
    if not data:
        raise ValidationError("No input data provided")
    validated_data = Policy.validate_input(data)
    if Policy.query.get(validated_data['policy_id']):
        raise ValidationError("Policy ID already exists")
    if not Policyholder.query.get(validated_data['policyholder_id']):
        raise ResourceNotFoundError("Policyholder not found")
    policy = Policy(**validated_data)
    db.session.add(policy)
    safe_commit()
    return jsonify({
        'policy_id': policy.policy_id,
        'policy_type': policy.policy_type,
        'coverage_amount': float(policy.coverage_amount),
        'start_date': str(policy.start_date),
        'end_date': str(policy.end_date),
        'policyholder_id': policy.policyholder_id
    }), 201

@app.route('/policies/<policy_id>', methods=['GET'])
def get_policy(policy_id):
    policy = Policy.query.get(policy_id)
    if not policy:
        raise ResourceNotFoundError("Policy not found")
    return jsonify({
        'policy_id': policy.policy_id,
        'policy_type': policy.policy_type,
        'coverage_amount': float(policy.coverage_amount),
        'start_date': str(policy.start_date),
        'end_date': str(policy.end_date),
        'policyholder_id': policy.policyholder_id
    }), 200

@app.route('/policies/', methods=['GET'])
def get_all_policies():
    policies = Policy.query.all()
    return jsonify([{
        'policy_id': p.policy_id,
        'policy_type': p.policy_type,
        'coverage_amount': float(p.coverage_amount),
        'start_date': str(p.start_date),
        'end_date': str(p.end_date),
        'policyholder_id': p.policyholder_id
    } for p in policies]), 200

@app.route('/policies/<policy_id>', methods=['PUT'])
def update_policy(policy_id):
    policy = Policy.query.get(policy_id)
    if not policy:
        raise ResourceNotFoundError("Policy not found")
    data = request.get_json()
    try:
        start_date = policy.start_date
        end_date = policy.end_date
        if 'start_date' in data:
            start_date = validate_date(data['start_date'])
        if 'end_date' in data:
            end_date = validate_date(data['end_date'])
        validate_date_range(start_date, end_date)
        if 'policy_type' in data:
            policy.policy_type = validate_string_field(data['policy_type'], 'Policy Type', 100)
        if 'coverage_amount' in data:
            policy.coverage_amount = validate_amount(data['coverage_amount'])
        policy.start_date = start_date
        policy.end_date = end_date
        safe_commit()
        return jsonify({
            'policy_id': policy.policy_id,
            'policy_type': policy.policy_type,
            'coverage_amount': float(policy.coverage_amount),
            'start_date': str(policy.start_date),
            'end_date': str(policy.end_date),
            'policyholder_id': policy.policyholder_id
        }), 200
    except Exception as e:
        db.session.rollback()
        raise e

@app.route('/policies/<policy_id>', methods=['DELETE'])
def delete_policy(policy_id):
    policy = Policy.query.get(policy_id)
    if not policy:
        raise ResourceNotFoundError("Policy not found")
    db.session.delete(policy)
    safe_commit()
    return jsonify({"message": "Policy deleted successfully"}), 200

@app.route('/claims', methods=['POST'])
def create_claim():
    data = request.get_json()
    if not data:
        raise ValidationError("No input data provided")
    validated_data = Claim.validate_input(data)
    if Claim.query.get(validated_data['claim_id']):
        raise ValidationError("Claim ID already exists")
    policy = Policy.query.get(validated_data['policy_id'])
    if not policy:
        raise ResourceNotFoundError("Policy not found")
    if validated_data['amount'] > policy.coverage_amount:
        raise ValidationError("Claim amount exceeds policy coverage")
    claim = Claim(**validated_data)
    db.session.add(claim)
    safe_commit()
    return jsonify({
        'claim_id': claim.claim_id,
        'description': claim.description,
        'amount': float(claim.amount),
        'date': str(claim.date),
        'status': claim.status,
        'policy_id': claim.policy_id
    }), 201

@app.route('/claims/<claim_id>', methods=['GET'])
def get_claim(claim_id):
    claim = Claim.query.get(claim_id)
    if not claim:
        raise ResourceNotFoundError("Claim not found")
    return jsonify({
        'claim_id': claim.claim_id,
        'description': claim.description,
        'amount': float(claim.amount),
        'date': str(claim.date),
        'status': claim.status,
        'policy_id': claim.policy_id
    }), 200

@app.route('/claims/', methods=['GET'])
def get_all_claims():
    claims = Claim.query.all()
    return jsonify([{
        'claim_id': claim.claim_id,
        'description': claim.description,
        'amount': float(claim.amount),
        'date': str(claim.date),
        'status': claim.status,
        'policy_id': claim.policy_id
    } for claim in claims]), 200

@app.route('/claims/<claim_id>', methods=['PUT'])
def update_claim(claim_id):
    claim = Claim.query.get(claim_id)
    if not claim:
        raise ResourceNotFoundError("Claim not found")
    data = request.get_json()
    try:
        if 'description' in data:
            claim.description = validate_string_field(data['description'], 'Description', 1000)
        if 'amount' in data:
            new_amount = validate_amount(data['amount'])
            policy = Policy.query.get(claim.policy_id)
            if new_amount > policy.coverage_amount:
                raise ValidationError("Claim amount exceeds policy coverage")
            claim.amount = new_amount
        if 'date' in data:
            claim.date = validate_date(data['date'])
        if 'status' in data:
            claim.status = validate_status(data['status'])
        safe_commit()
        return jsonify({
            'claim_id': claim.claim_id,
            'description': claim.description,
            'amount': float(claim.amount),
            'date': str(claim.date),
            'status': claim.status,
            'policy_id': claim.policy_id
        }), 200
    except Exception as e:
        db.session.rollback()
        raise e

@app.route('/claims/<claim_id>', methods=['DELETE'])
def delete_claim(claim_id):
    claim = Claim.query.get(claim_id)
    if not claim:
        raise ResourceNotFoundError("Claim not found")
    db.session.delete(claim)
    safe_commit()
    return jsonify({"message": "Claim deleted successfully"}), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True,threaded=True)