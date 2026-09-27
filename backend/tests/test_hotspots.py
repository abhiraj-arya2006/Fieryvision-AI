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
    assert data['total'] >= 3
    # Verify multiple continents are present
    continents = {item['continent'] for item in data['items']}
    assert len(continents) >= 2

def test_continent_filtering():
    res = client.get('/api/hotspots')
    assert res.status_code == 200
    items = res.json().get('items', [])
    assert len(items) > 0
    target_continent = items[0]['continent']
    target_country = items[0]['country']

    # Filter by target continent
    res_cont = client.get(f'/api/hotspots?continent={target_continent}')
    assert res_cont.status_code == 200
    data_cont = res_cont.json()
    assert data_cont['total'] >= 1
    for h in data_cont['items']:
        assert h['continent'] == target_continent

    # Filter by target country
    res_country = client.get(f'/api/hotspots?country={target_country}')
    assert res_country.status_code == 200
    data_country = res_country.json()
    assert data_country['total'] >= 1
    for h in data_country['items']:
        assert h['country'] == target_country

def test_hotspot_analytics():
    response = client.get('/api/hotspots/analytics')
    assert response.status_code == 200
    data = response.json()
    assert 'total_active_hotspots' in data
    assert data['total_active_hotspots'] >= 3
    assert 'emerging_hotspots_count' in data
    assert 'persistent_hotspots_count' in data
    assert 'continent_breakdown' in data
    assert len(data['continent_breakdown']) >= 2
    assert 'largest_hotspot' in data
    assert 'fastest_growing_hotspot' in data

def test_hotspot_alerts():
    response = client.get('/api/hotspots/alerts')
    assert response.status_code == 200
    alerts = response.json()
    assert isinstance(alerts, list)

def test_hotspot_detail_and_history():
    res_list = client.get('/api/hotspots')
    items = res_list.json()['items']
    assert len(items) > 0
    target_id = items[0]['id']

    response = client.get(f'/api/hotspots/{target_id}')
    assert response.status_code == 200
    hs = response.json()
    assert hs['id'] == target_id
    assert 'reason_codes' in hs
    assert 'sample_detections' in hs
    assert 'timeline_snapshots' in hs

    res_hist = client.get(f'/api/hotspots/{target_id}/history')
    assert res_hist.status_code == 200
    snaps = res_hist.json()
    assert isinstance(snaps, list)
    assert len(snaps) >= 1

def test_hotspot_bbox_query():
    # Query covering western United States (lat 30-45, lon -125 to -100)
    response = client.get('/api/hotspots/bbox?min_lat=30.0&min_lon=-125.0&max_lat=45.0&max_lon=-100.0')
    assert response.status_code == 200
    items = response.json()
    assert len(items) >= 1

def test_hotspot_nearby_query():
    res = client.get('/api/hotspots')
    assert res.status_code == 200
    items = res.json().get('items', [])
    assert len(items) > 0
    first_hs = items[0]
    lat = first_hs['centroid_lat']
    lon = first_hs['centroid_lon']

    # Query within 100km of the hotspot's centroid
    response = client.get(f'/api/hotspots/nearby?latitude={lat}&longitude={lon}&radius_km=100.0')
    assert response.status_code == 200
    nearby_items = response.json()
    assert len(nearby_items) >= 1
    assert any(h['id'] == first_hs['id'] for h in nearby_items)

def test_hotspot_shortcuts():
    active = client.get('/api/hotspots/active').json()
    assert len(active) >= 1
