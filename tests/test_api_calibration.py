from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)

def test_api_calibration_shape():
    response = client.get("/api/calibration")
    assert response.status_code == 200
    
    data = response.json()
    
    # Assert top-level keys
    assert "version" in data
    assert "degradation_slopes" in data
    assert "compound_deltas" in data
    assert "fuel_burn_effect" in data
    assert "pit_loss" in data
    
    # Assert provenance-aware structure
    soft_slope = data["degradation_slopes"]["SOFT"]
    assert "value" in soft_slope
    assert "source" in soft_slope
    assert "quality_status" in soft_slope
    
    pit_loss = data["pit_loss"]
    assert "value" in pit_loss
    assert "source" in pit_loss
    assert "quality_status" in pit_loss
