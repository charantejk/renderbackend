from entities import Policyholder, Policy, Claim
from datetime import date
from typing import Dict, Optional

class ClaimsManager:
    def __init__(self):
        self.policyholders: Dict[str, Policyholder] = {}
        self.policies: Dict[str, Policy] = {}
        self.claims: Dict[str, Claim] = {}

    # Policyholder CRUD operations
    def create_policyholder(self, policyholder: Policyholder):
        if policyholder.policyholder_id in self.policyholders:
            raise ValueError("Policyholder ID already exists")
        self.policyholders[policyholder.policyholder_id] = policyholder

    def get_policyholder(self, policyholder_id: str) -> Optional[Policyholder]:
        return self.policyholders.get(policyholder_id)

    def update_policyholder(self, policyholder_id: str, **kwargs):
        if policyholder_id not in self.policyholders:
            raise ValueError("Policyholder not found")
        ph = self.policyholders[policyholder_id]
        for key, value in kwargs.items():
            if hasattr(ph, key):
                setattr(ph, key, value)
            else:
                raise AttributeError(f"Invalid field: {key}")

    def delete_policyholder(self, policyholder_id: str):
        if policyholder_id not in self.policyholders:
            raise ValueError("Policyholder not found")
        if any(p.policyholder_id == policyholder_id for p in self.policies.values()):
            raise ValueError("Policyholder has existing policies")
        del self.policyholders[policyholder_id]

    # Policy CRUD operations
    def create_policy(self, policy: Policy):
        if policy.policy_id in self.policies:
            raise ValueError("Policy ID already exists")
        if policy.policyholder_id not in self.policyholders:
            raise ValueError("Policyholder does not exist")
        if policy.start_date > policy.end_date:
            raise ValueError("Invalid policy dates")
        self.policies[policy.policy_id] = policy

    def get_policy(self, policy_id: str) -> Optional[Policy]:
        return self.policies.get(policy_id)

    def update_policy(self, policy_id: str, **kwargs):
        if policy_id not in self.policies:
            raise ValueError("Policy not found")
        policy = self.policies[policy_id]
        for key, value in kwargs.items():
            if hasattr(policy, key):
                setattr(policy, key, value)
            else:
                raise AttributeError(f"Invalid field: {key}")

    def delete_policy(self, policy_id: str):
        if policy_id not in self.policies:
            raise ValueError("Policy not found")
        if any(c.policy_id == policy_id for c in self.claims.values()):
            raise ValueError("Policy has existing claims")
        del self.policies[policy_id]

    # Claim CRUD operations
    def create_claim(self, claim: Claim):
        if claim.claim_id in self.claims:
            raise ValueError("Claim ID already exists")
        policy = self.policies.get(claim.policy_id)
        if not policy:
            raise ValueError("Policy does not exist")
        if claim.amount > policy.coverage_amount:
            raise ValueError("Claim exceeds policy coverage")
        if claim.date < policy.start_date or claim.date > policy.end_date:
            raise ValueError("Claim date outside policy period")
        self.claims[claim.claim_id] = claim

    def get_claim(self, claim_id: str) -> Optional[Claim]:
        return self.claims.get(claim_id)

    def update_claim(self, claim_id: str, **kwargs):
        if claim_id not in self.claims:
            raise ValueError("Claim not found")
        claim = self.claims[claim_id]
        for key, value in kwargs.items():
            if hasattr(claim, key):
                setattr(claim, key, value)
            else:
                raise AttributeError(f"Invalid field: {key}")

    def delete_claim(self, claim_id: str):
        if claim_id not in self.claims:
            raise ValueError("Claim not found")
        del self.claims[claim_id]