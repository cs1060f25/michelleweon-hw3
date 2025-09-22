"""
Test suite for StudyStreak application
"""

import pytest
import json
import sqlite3
from datetime import datetime, timedelta
from app import app, init_db

@pytest.fixture
def client():
    """Create test client"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def init_test_db():
    """Initialize test database"""
    init_db()

def test_create_user(client, init_test_db):
    """Test user creation"""
    user_data = {
        'username': 'testuser',
        'email': 'test@example.com',
        'preferences': {
            'preferred_study_hours': [9, 14, 19],
            'morning_preference': 0.8
        }
    }
    
    response = client.post('/api/users', 
                          data=json.dumps(user_data),
                          content_type='application/json')
    
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['username'] == 'testuser'
    assert data['email'] == 'test@example.com'

def test_create_group(client, init_test_db):
    """Test group creation"""
    # First create a user
    user_data = {
        'username': 'testuser',
        'email': 'test@example.com',
        'preferences': {}
    }
    client.post('/api/users', 
                data=json.dumps(user_data),
                content_type='application/json')
    
    # Create a group
    group_data = {
        'name': 'Study Group Alpha',
        'description': 'A test study group',
        'created_by': 1
    }
    
    response = client.post('/api/groups',
                          data=json.dumps(group_data),
                          content_type='application/json')
    
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['name'] == 'Study Group Alpha'

def test_create_study_session(client, init_test_db):
    """Test study session creation"""
    # First create a user
    user_data = {
        'username': 'testuser',
        'email': 'test@example.com',
        'preferences': {}
    }
    client.post('/api/users', 
                data=json.dumps(user_data),
                content_type='application/json')
    
    # Create a study session
    session_data = {
        'user_id': 1,
        'start_time': datetime.now().isoformat(),
        'end_time': (datetime.now() + timedelta(hours=2)).isoformat(),
        'subject': 'Mathematics'
    }
    
    response = client.post('/api/study-sessions',
                          data=json.dumps(session_data),
                          content_type='application/json')
    
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['subject'] == 'Mathematics'

def test_complete_study_session(client, init_test_db):
    """Test completing a study session"""
    # First create a user and session
    user_data = {
        'username': 'testuser',
        'email': 'test@example.com',
        'preferences': {}
    }
    client.post('/api/users', 
                data=json.dumps(user_data),
                content_type='application/json')
    
    session_data = {
        'user_id': 1,
        'start_time': datetime.now().isoformat(),
        'end_time': (datetime.now() + timedelta(hours=2)).isoformat(),
        'subject': 'Mathematics'
    }
    create_response = client.post('/api/study-sessions',
                                 data=json.dumps(session_data),
                                 content_type='application/json')
    session_id = json.loads(create_response.data)['id']
    
    # Complete the session
    response = client.put(f'/api/study-sessions/{session_id}/complete')
    assert response.status_code == 200

def test_get_dashboard(client, init_test_db):
    """Test dashboard data retrieval"""
    # First create a user
    user_data = {
        'username': 'testuser',
        'email': 'test@example.com',
        'preferences': {}
    }
    client.post('/api/users', 
                data=json.dumps(user_data),
                content_type='application/json')
    
    response = client.get('/api/dashboard/1')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'user' in data
    assert 'streaks' in data
    assert 'recent_sessions' in data

def test_schedule_recommendation(client, init_test_db):
    """Test smart schedule recommendations"""
    # First create a user
    user_data = {
        'username': 'testuser',
        'email': 'test@example.com',
        'preferences': {
            'preferred_study_hours': [9, 14, 19],
            'preferred_days': [0, 1, 2, 3, 4]
        }
    }
    client.post('/api/users', 
                data=json.dumps(user_data),
                content_type='application/json')
    
    # Get schedule recommendations
    request_data = {
        'user_id': 1,
        'preferences': {}
    }
    
    response = client.post('/api/schedule/recommend',
                          data=json.dumps(request_data),
                          content_type='application/json')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'recommended_sessions' in data
    assert len(data['recommended_sessions']) > 0

def test_habit_progress(client, init_test_db):
    """Test habit progress tracking"""
    # First create a user
    user_data = {
        'username': 'testuser',
        'email': 'test@example.com',
        'preferences': {}
    }
    client.post('/api/users', 
                data=json.dumps(user_data),
                content_type='application/json')
    
    response = client.get('/api/dashboard/1/habit-progress')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'progress' in data
    assert 'rewards' in data

def test_join_group(client, init_test_db):
    """Test joining a group"""
    # First create a user and group
    user_data = {
        'username': 'testuser',
        'email': 'test@example.com',
        'preferences': {}
    }
    client.post('/api/users', 
                data=json.dumps(user_data),
                content_type='application/json')
    
    group_data = {
        'name': 'Study Group Alpha',
        'description': 'A test study group',
        'created_by': 1
    }
    client.post('/api/groups',
                data=json.dumps(group_data),
                content_type='application/json')
    
    # Create another user to join the group
    user2_data = {
        'username': 'testuser2',
        'email': 'test2@example.com',
        'preferences': {}
    }
    client.post('/api/users', 
                data=json.dumps(user2_data),
                content_type='application/json')
    
    # Join the group
    join_data = {'user_id': 2}
    response = client.post('/api/groups/1/join',
                          data=json.dumps(join_data),
                          content_type='application/json')
    
    assert response.status_code == 200

def test_duplicate_user_creation(client, init_test_db):
    """Test that duplicate users are rejected"""
    user_data = {
        'username': 'testuser',
        'email': 'test@example.com',
        'preferences': {}
    }
    
    # Create first user
    response1 = client.post('/api/users', 
                           data=json.dumps(user_data),
                           content_type='application/json')
    assert response1.status_code == 201
    
    # Try to create duplicate user
    response2 = client.post('/api/users', 
                           data=json.dumps(user_data),
                           content_type='application/json')
    assert response2.status_code == 400

def test_invalid_user_id(client, init_test_db):
    """Test handling of invalid user IDs"""
    response = client.get('/api/dashboard/999')
    assert response.status_code == 200  # Should return error in data, not 404
    data = json.loads(response.data)
    assert 'error' in data

if __name__ == '__main__':
    pytest.main([__file__])
