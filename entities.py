from dataclasses import dataclass
from datetime import date

@dataclass
class Policyholder:
    policyholder_id: str
    name: str
    contact_info: str

@dataclass
class Policy:
    policy_id: str
    policy_type: str
    coverage_amount: float
    start_date: date
    end_date: date
    policyholder_id: str

@dataclass
class Claim:
    claim_id: str
    description: str
    amount: float
    date: date
    status: str
    policy_id: str