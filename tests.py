import pytest
from datetime import date
from manager import ClaimsManager
from entities import Policyholder, Policy, Claim

def test_create_claim():
    manager = ClaimsManager()
    ph = Policyholder("ph1", "Alice", "alice@email.com")
    manager.create_policyholder(ph)
    
    policy = Policy("p1", "Home", 100000, date(2024,1,1), date(2025,1,1), "ph1")
    manager.create_policy(policy)
    
    claim = Claim("c1", "Fire Damage", 50000, date(2024,6,1), "Pending", "p1")
    manager.create_claim(claim)
    
    assert manager.claims["c1"].amount == 50000

def test_invalid_claim_amount():
    manager = ClaimsManager()
    # Add similar setup
    with pytest.raises(ValueError):
        claim = Claim("c1", "Damage", 200000, date(2024,6,1), "Pending", "p1")
        manager.create_claim(claim)