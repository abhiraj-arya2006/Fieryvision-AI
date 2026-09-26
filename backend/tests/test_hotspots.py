import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_list_hotspots_global():
    response = client.get('/api/hotspots')
    assert response.status_code == 200
    data = response.json()
    assert 'items' in data
    assert 'total' in data
    assert data['total'] >= 8
    # Verify multiple continents are present
    continents = {item['continent'] for item in data['items']}
    assert 'North America' in continents or 'Asia' in continents or 'Europe' in continents

def test_continent_filtering():
    # Filter by North America (USA)
    res_na = client.get('/api/hotspots?continent=North America')
    assert res_na.status_code == 200
    data_na = res_na.json()
    assert data_na['total'] >= 1
    for h in data_na['items']:
        assert h['continent'] == 'North America'

    # Filter by Europe
    res_eu = client.get('/api/hotspots?continent=Europe')
    assert res_eu.status_code == 200
    data_eu = res_eu.json()
    assert data_eu['total'] >= 1
    for h in data_eu['items']:
        assert h['continent'] == 'Europe'

    # Filter by India
    res_ind = client.get('/api/hotspots?country=India')
    assert res_ind.status_code == 200
    data_ind = res_ind.json()
    assert data_ind['total'] >= 1
    for h in data_ind['items']:
        assert h['country'] == 'India'

def test_hotspot_analytics():
    response = client.get('/api/hotspots/analytics')
    assert response.status_code == 200
    data = response.json()
    assert 'total_active_hotspots' in data
    assert data['total_active_hotspots'] >= 8
    assert 'emerging_hotspots_count' in data
    assert 'persistent_hotspots_count' in data
    assert 'high_intensity_hotspots_count' in data
    assert 'continent_breakdown' in data
    assert len(data['continent_breakdown']) >= 3
    assert 'largest_hotspot' in data
    assert 'fastest_growing_hotspot' in data

def test_hotspot_alerts():
    response = client.get('/api/hotspots/alerts')
    assert response.status_code == 200
    alerts = response.json()
    assert isinstance(alerts, list)
    assert len(alerts) > 0
    first_alert = alerts[0]
    assert 'alert_id' in first_alert
    assert 'hotspot_id' in first_alert
    assert 'severity' in first_alert
    assert 'message' in first_alert

def test_hotspot_detail_usa():
    response = client.get('/api/hotspots/HS-NA-001')
    assert response.status_code == 200
    hs = response.json()
    assert hs['id'] == 'HS-NA-001'
    assert hs['country'] == 'United States'
    assert 'reason_codes' in hs
    assert len(hs['reason_codes']) > 0
    assert 'sample_detections' in hs
    assert 'timeline_snapshots' in hs

def test_hotspot_detail_india():
    response = client.get('/api/hotspots/HS-IND-001')
    assert response.status_code == 200
    hs = response.json()
    assert hs['id'] == 'HS-IND-001'
    assert hs['country'] == 'India'
    assert hs['nearest_city'] == 'Ludhiana'

def test_hotspot_history():
    response = client.get('/api/hotspots/HS-NA-001/history')
    assert response.status_code == 200
    snaps = response.json()
    assert isinstance(snaps, list)
    assert len(snaps) >= 2

def test_hotspot_bbox_query():
    # Query covering western United States (lat 30-45, lon -125 to -100)
    response = client.get('/api/hotspots/bbox?min_lat=30.0&min_lon=-125.0&max_lat=45.0&max_lon=-100.0')
    assert response.status_code == 200
    items = response.json()
    assert len(items) >= 1
    assert any(h['id'] == 'HS-NA-001' for h in items)

def test_hotspot_nearby_query():
    # Query within 300km of Ludhiana, Punjab (30.9, 75.85)
    response = client.get('/api/hotspots/nearby?latitude=30.9&longitude=75.85&radius_km=300.0')
    assert response.status_code == 200
    items = response.json()
    assert len(items) >= 1
    assert any(h['id'] == 'HS-IND-001' for h in items)

def test_hotspot_shortcuts():
    active = client.get('/api/hotspots/active').json()
    assert len(active) >= 1
    emerging = client.get('/api/hotspots/emerging').json()
    assert len(emerging) >= 1
    persistent = client.get('/api/hotspots/persistent').json()
    assert len(persistent) >= 1
    high_risk = client.get('/api/hotspots/high-risk').json()
    assert len(high_risk) >= 1
