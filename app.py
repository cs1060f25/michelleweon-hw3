from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_cors import CORS
import sqlite3
import json
from datetime import datetime, timedelta
import os
import hashlib
import secrets
from dotenv import load_dotenv
from calendar_integration import CalendarIntegration, SmartScheduler
from dashboard import DashboardManager, HabitTracker

load_dotenv()

app = Flask(__name__)
CORS(app)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-this')

# Initialize managers
dashboard_manager = DashboardManager()
habit_tracker = HabitTracker()
calendar_integration = CalendarIntegration()
smart_scheduler = SmartScheduler(calendar_integration)

# Password hashing functions
def hash_password(password):
    """Hash a password using SHA-256 with salt"""
    salt = secrets.token_hex(16)
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}:{password_hash}"

def verify_password(password, stored_hash):
    """Verify a password against its hash"""
    try:
        salt, password_hash = stored_hash.split(':')
        return hashlib.sha256((password + salt).encode()).hexdigest() == password_hash
    except:
        return False

def require_auth(f):
    """Decorator to require authentication"""
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# Database initialization
def init_db():
    conn = sqlite3.connect('accountability.db')
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            preferences TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Check if password_hash column exists, if not add it
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'password_hash' not in columns:
        print("Adding password_hash column to existing users table...")
        cursor.execute('ALTER TABLE users ADD COLUMN password_hash TEXT')
        # Set default for existing users
        cursor.execute('UPDATE users SET password_hash = ? WHERE password_hash IS NULL', 
                      ('default:needs_reset',))
    
    # Groups table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    ''')
    
    # Group members table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS group_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER,
            user_id INTEGER,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (group_id) REFERENCES groups (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Study sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS study_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            subject TEXT,
            completed BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Check if new columns exist in study_sessions table, add them if not
    cursor.execute("PRAGMA table_info(study_sessions)")
    columns = [column[1] for column in cursor.fetchall()]
    
    new_columns = [
        ('title', 'TEXT'),
        ('description', 'TEXT'),
        ('duration_minutes', 'INTEGER'),
        ('location', 'TEXT'),
        ('notes', 'TEXT'),
        ('completed_at', 'TIMESTAMP')
    ]
    
    for col_name, col_type in new_columns:
        if col_name not in columns:
            print(f"Adding {col_name} column to study_sessions table...")
            cursor.execute(f'ALTER TABLE study_sessions ADD COLUMN {col_name} {col_type}')
    
    # Streaks table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS streaks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            group_id INTEGER,
            current_streak INTEGER DEFAULT 0,
            longest_streak INTEGER DEFAULT 0,
            last_activity TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (group_id) REFERENCES groups (id)
        )
    ''')
    
    # Accomplishments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accomplishments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            group_id INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            category TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (group_id) REFERENCES groups (id)
        )
    ''')
    
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/group')
def group_details():
    return render_template('group_details.html')

@app.route('/schedule')
def schedule():
    return render_template('schedule.html')

# User management endpoints
@app.route('/api/users', methods=['POST'])
def create_user():
    data = request.get_json()
    
    # Validate required fields
    if not all(key in data for key in ['username', 'email']):
        return jsonify({'error': 'Username and email are required'}), 400
    
    # Hash the password if provided, otherwise use default
    if 'password' in data and data['password']:
        password_hash = hash_password(data['password'])
    else:
        password_hash = 'default:needs_reset'
    
    conn = sqlite3.connect('accountability.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, preferences)
            VALUES (?, ?, ?, ?)
        ''', (data['username'], data['email'], password_hash, json.dumps(data.get('preferences', {}))))
        
        user_id = cursor.lastrowid
        conn.commit()
        
        # Set session
        session['user_id'] = user_id
        session['username'] = data['username']
        
        return jsonify({
            'id': user_id,
            'username': data['username'],
            'email': data['email'],
            'preferences': data.get('preferences', {}),
            'message': 'Account created successfully'
        }), 201
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Username or email already exists'}), 400
    finally:
        conn.close()

# Authentication endpoints
@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not all(key in data for key in ['email', 'password']):
        return jsonify({'error': 'Email and password required'}), 400
    
    conn = sqlite3.connect('accountability.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT id, username, email, password_hash, preferences FROM users WHERE email = ?', (data['email'],))
        user = cursor.fetchone()
        
        if user and verify_password(data['password'], user[3]):
            # Set session
            session['user_id'] = user[0]
            session['username'] = user[1]
            
            return jsonify({
                'id': user[0],
                'username': user[1],
                'email': user[2],
                'preferences': json.loads(user[4]) if user[4] else {},
                'message': 'Login successful'
            }), 200
        else:
            return jsonify({'error': 'Invalid email or password'}), 401
    finally:
        conn.close()

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out successfully'}), 200

@app.route('/api/auth/me', methods=['GET'])
def get_current_user():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    conn = sqlite3.connect('accountability.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT id, username, email, preferences FROM users WHERE id = ?', (session['user_id'],))
        user = cursor.fetchone()
        
        if user:
            return jsonify({
                'id': user[0],
                'username': user[1],
                'email': user[2],
                'preferences': json.loads(user[3]) if user[3] else {}
            })
        else:
            return jsonify({'error': 'User not found'}), 404
    finally:
        conn.close()

@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    conn = sqlite3.connect('accountability.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, username, email, preferences, created_at FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return jsonify({
            'id': user[0],
            'username': user[1],
            'email': user[2],
            'preferences': json.loads(user[3]) if user[3] else {},
            'created_at': user[4]
        })
    else:
        return jsonify({'error': 'User not found'}), 404

# Group management endpoints
@app.route('/api/groups', methods=['GET'])
def get_all_groups():
    """Get all available groups"""
    conn = sqlite3.connect('accountability.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT g.id, g.name, g.description, g.created_by, g.created_at,
                   COUNT(gm.user_id) as member_count
            FROM groups g
            LEFT JOIN group_members gm ON g.id = gm.group_id
            GROUP BY g.id, g.name, g.description, g.created_by, g.created_at
            ORDER BY g.created_at DESC
        ''')
        
        groups = cursor.fetchall()
        
        return jsonify([{
            'id': group[0],
            'name': group[1],
            'description': group[2],
            'created_by': group[3],
            'created_at': group[4],
            'member_count': group[5]
        } for group in groups])
    finally:
        conn.close()

@app.route('/api/groups', methods=['POST'])
def create_group():
    data = request.get_json()
    conn = sqlite3.connect('accountability.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO groups (name, description, created_by)
            VALUES (?, ?, ?)
        ''', (data['name'], data.get('description', ''), data['created_by']))
        
        group_id = cursor.lastrowid
        
        # Add creator as member
        cursor.execute('''
            INSERT INTO group_members (group_id, user_id)
            VALUES (?, ?)
        ''', (group_id, data['created_by']))
        
        conn.commit()
        
        return jsonify({
            'id': group_id,
            'name': data['name'],
            'description': data.get('description', ''),
            'created_by': data['created_by']
        }), 201
    finally:
        conn.close()

@app.route('/api/groups/<int:group_id>', methods=['GET'])
def get_group(group_id):
    """Get details for a specific group"""
    conn = sqlite3.connect('accountability.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT g.id, g.name, g.description, g.created_by, g.created_at,
                   COUNT(gm.user_id) as member_count
            FROM groups g
            LEFT JOIN group_members gm ON g.id = gm.group_id
            WHERE g.id = ?
            GROUP BY g.id, g.name, g.description, g.created_by, g.created_at
        ''', (group_id,))
        
        group = cursor.fetchone()
        
        if group:
            return jsonify({
                'id': group[0],
                'name': group[1],
                'description': group[2],
                'created_by': group[3],
                'created_at': group[4],
                'member_count': group[5]
            })
        else:
            return jsonify({'error': 'Group not found'}), 404
    finally:
        conn.close()

@app.route('/api/groups/<int:group_id>/join', methods=['POST'])
def join_group(group_id):
    data = request.get_json()
    conn = sqlite3.connect('accountability.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO group_members (group_id, user_id)
            VALUES (?, ?)
        ''', (group_id, data['user_id']))
        
        conn.commit()
        return jsonify({'message': 'Successfully joined group'}), 200
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Already a member of this group'}), 400
    finally:
        conn.close()

# Study session endpoints
@app.route('/api/study-sessions', methods=['POST'])
def create_study_session():
    data = request.get_json()
    conn = sqlite3.connect('accountability.db')
    cursor = conn.cursor()
    
    try:
        # Create study session in database
        cursor.execute('''
            INSERT INTO study_sessions (user_id, start_time, end_time, subject, title, description, duration_minutes, location, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['user_id'],
            data['start_time'],
            data['end_time'],
            data['subject'],
            data.get('title', data['subject']),
            data.get('description', ''),
            data.get('duration_minutes', 120),
            data.get('location', ''),
            data.get('notes', '')
        ))
        
        session_id = cursor.lastrowid
        conn.commit()
        
        # Create Google Calendar event if user has calendar integration
        google_event = None
        if data.get('add_to_calendar', False):
            try:
                from datetime import datetime
                start_time = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(data['end_time'].replace('Z', '+00:00'))
                
                google_event = calendar_integration.create_google_event(
                    title=data.get('title', data['subject']),
                    description=data.get('description', data.get('notes', '')),
                    start_time=start_time,
                    end_time=end_time
                )
            except Exception as e:
                print(f"Failed to create Google Calendar event: {e}")
        
        return jsonify({
            'id': session_id,
            'user_id': data['user_id'],
            'start_time': data['start_time'],
            'end_time': data['end_time'],
            'subject': data['subject'],
            'title': data.get('title', data['subject']),
            'description': data.get('description', ''),
            'duration_minutes': data.get('duration_minutes', 120),
            'location': data.get('location', ''),
            'notes': data.get('notes', ''),
            'google_event': google_event
        }), 201
    finally:
        conn.close()

@app.route('/api/study-sessions/suggest', methods=['POST'])
def suggest_study_sessions():
    """AI-powered study session suggestions based on work description"""
    data = request.get_json()
    
    try:
        # Get user preferences
        conn = sqlite3.connect('accountability.db')
        cursor = conn.cursor()
        cursor.execute('SELECT study_preferences, primary_subject FROM users WHERE id = ?', (data['user_id'],))
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Parse user preferences
        preferences = {
            'preferred_study_hours': [9, 14, 19],  # Default hours
            'subjects': [user[1]] if user[1] else ['General Study']
        }
        
        if user[0]:
            try:
                import json
                user_prefs = json.loads(user[0])
                preferences.update(user_prefs)
            except:
                pass
        
        # Generate suggestions
        suggestions = smart_scheduler.suggest_study_sessions_from_work(
            data['work_description'], 
            preferences
        )
        
        return jsonify({
            'suggestions': suggestions,
            'work_description': data['work_description']
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/study-sessions/<int:user_id>', methods=['GET'])
def get_user_study_sessions(user_id):
    """Get all study sessions for a user"""
    conn = sqlite3.connect('accountability.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT id, subject, title, description, duration_minutes, start_time, end_time,
                   location, notes, created_at, completed
            FROM study_sessions 
            WHERE user_id = ? 
            ORDER BY start_time DESC
        ''', (user_id,))
        
        sessions = []
        for row in cursor.fetchall():
            sessions.append({
                'id': row[0],
                'subject': row[1],
                'title': row[2],
                'description': row[3],
                'duration_minutes': row[4],
                'start_time': row[5],
                'end_time': row[6],
                'location': row[7],
                'notes': row[8],
                'created_at': row[9],
                'completed': bool(row[10]) if row[10] is not None else False
            })
        
        return jsonify({'sessions': sessions}), 200
    finally:
        conn.close()

@app.route('/api/study-sessions/<int:session_id>/complete', methods=['PUT'])
def complete_study_session(session_id):
    conn = sqlite3.connect('accountability.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE study_sessions 
            SET completed = TRUE, completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (session_id,))
        
        if cursor.rowcount == 0:
            return jsonify({'error': 'Session not found'}), 404
        
        conn.commit()
        return jsonify({'message': 'Study session completed'}), 200
    finally:
        conn.close()

@app.route('/api/study-sessions/<int:session_id>', methods=['DELETE'])
def delete_study_session(session_id):
    conn = sqlite3.connect('accountability.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('DELETE FROM study_sessions WHERE id = ?', (session_id,))
        
        if cursor.rowcount == 0:
            return jsonify({'error': 'Session not found'}), 404
        
        conn.commit()
        return jsonify({'message': 'Study session deleted'}), 200
    finally:
        conn.close()

# Streak management
@app.route('/api/streaks/<int:user_id>', methods=['GET'])
def get_user_streaks(user_id):
    conn = sqlite3.connect('accountability.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT s.*, g.name as group_name
        FROM streaks s
        LEFT JOIN groups g ON s.group_id = g.id
        WHERE s.user_id = ?
    ''', (user_id,))
    
    streaks = cursor.fetchall()
    conn.close()
    
    return jsonify([{
        'id': streak[0],
        'user_id': streak[1],
        'group_id': streak[2],
        'current_streak': streak[3],
        'longest_streak': streak[4],
        'last_activity': streak[5],
        'group_name': streak[7]
    } for streak in streaks])

# Dashboard endpoints
@app.route('/api/dashboard/<int:user_id>', methods=['GET'])
def get_dashboard(user_id):
    """Get comprehensive dashboard data for a user"""
    dashboard_data = dashboard_manager.get_user_dashboard(user_id)
    return jsonify(dashboard_data)

@app.route('/api/dashboard/<int:user_id>/habit-progress', methods=['GET'])
def get_habit_progress(user_id):
    """Get habit formation progress for a user"""
    progress = habit_tracker.track_habit_progress(user_id)
    rewards = habit_tracker.get_milestone_rewards(progress)
    
    return jsonify({
        'progress': progress,
        'rewards': rewards
    })

@app.route('/api/dashboard/<int:user_id>/weekly-progress', methods=['GET'])
def get_weekly_progress(user_id):
    """Get weekly progress data for a user"""
    weeks = request.args.get('weeks', 4, type=int)
    progress = dashboard_manager.get_weekly_progress(user_id, weeks)
    return jsonify(progress)

# Group and social features
@app.route('/api/groups/<int:group_id>/leaderboard', methods=['GET'])
def get_group_leaderboard(group_id):
    """Get leaderboard for a group"""
    leaderboard = dashboard_manager.get_group_leaderboard(group_id)
    return jsonify(leaderboard)

@app.route('/api/groups/<int:group_id>/challenges', methods=['POST'])
def create_challenge(group_id):
    """Create a study challenge for a group"""
    data = request.get_json()
    success = dashboard_manager.create_study_challenge(group_id, data)
    
    if success:
        return jsonify({'message': 'Challenge created successfully'}), 201
    else:
        return jsonify({'error': 'Failed to create challenge'}), 500

# Calendar integration endpoints
@app.route('/api/calendar/authenticate', methods=['POST'])
def authenticate_calendar():
    """Authenticate with Google Calendar"""
    data = request.get_json()
    calendar_type = data.get('type', 'google')
    
    if calendar_type == 'google':
        success = calendar_integration.authenticate_google()
        return jsonify({'success': success})
    else:
        return jsonify({'error': 'Unsupported calendar type'}), 400

@app.route('/api/calendar/events', methods=['GET'])
def get_calendar_events():
    """Get events from connected calendars"""
    user_id = request.args.get('user_id', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not all([user_id, start_date, end_date]):
        return jsonify({'error': 'Missing required parameters'}), 400
    
    start_time = datetime.fromisoformat(start_date)
    end_time = datetime.fromisoformat(end_date)
    
    # Get user's calendar URLs from preferences
    conn = sqlite3.connect('accountability.db')
    cursor = conn.cursor()
    cursor.execute('SELECT preferences FROM users WHERE id = ?', (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    
    if not user_data:
        return jsonify({'error': 'User not found'}), 404
    
    preferences = json.loads(user_data[0]) if user_data[0] else {}
    ical_urls = preferences.get('ical_urls', [])
    
    events = calendar_integration.get_all_events(ical_urls, start_time, end_time)
    return jsonify(events)

# Smart scheduler endpoint
@app.route('/api/schedule/recommend', methods=['POST'])
def recommend_schedule():
    """Get smart schedule recommendations"""
    data = request.get_json()
    user_id = data['user_id']
    preferences = data.get('preferences', {})
    
    # Get user preferences from database
    conn = sqlite3.connect('accountability.db')
    cursor = conn.cursor()
    cursor.execute('SELECT preferences FROM users WHERE id = ?', (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    
    if user_data and user_data[0]:
        db_preferences = json.loads(user_data[0])
        # Merge with provided preferences
        preferences = {**db_preferences, **preferences}
    
    # Get smart recommendations
    recommendations = smart_scheduler.find_optimal_study_times(preferences)
    
    return jsonify({
        'recommended_sessions': recommendations,
        'user_id': user_id
    })

# Accomplishments endpoints
@app.route('/api/accomplishments', methods=['POST'])
def create_accomplishment():
    """Create a new accomplishment post"""
    data = request.get_json()
    
    if not all(key in data for key in ['user_id', 'group_id', 'title']):
        return jsonify({'error': 'Missing required fields'}), 400
    
    conn = sqlite3.connect('accountability.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO accomplishments (user_id, group_id, title, description, category)
            VALUES (?, ?, ?, ?, ?)
        ''', (data['user_id'], data['group_id'], data['title'], 
              data.get('description', ''), data.get('category', 'general')))
        
        accomplishment_id = cursor.lastrowid
        conn.commit()
        
        # Update streak for this user in this group
        dashboard_manager.update_streak(data['user_id'], data['group_id'])
        
        return jsonify({
            'id': accomplishment_id,
            'user_id': data['user_id'],
            'group_id': data['group_id'],
            'title': data['title'],
            'description': data.get('description', ''),
            'category': data.get('category', 'general'),
            'created_at': datetime.now().isoformat()
        }), 201
    finally:
        conn.close()

@app.route('/api/groups/<int:group_id>/accomplishments', methods=['GET'])
def get_group_accomplishments(group_id):
    """Get all accomplishments for a specific group"""
    conn = sqlite3.connect('accountability.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT a.id, a.user_id, a.group_id, a.title, a.description, a.category, a.created_at,
                   u.username
            FROM accomplishments a
            JOIN users u ON a.user_id = u.id
            WHERE a.group_id = ?
            ORDER BY a.created_at DESC
            LIMIT 50
        ''', (group_id,))
        
        accomplishments = cursor.fetchall()
        
        return jsonify([{
            'id': acc[0],
            'user_id': acc[1],
            'group_id': acc[2],
            'title': acc[3],
            'description': acc[4],
            'category': acc[5],
            'created_at': acc[6],
            'username': acc[7]
        } for acc in accomplishments])
    finally:
        conn.close()

@app.route('/api/groups/<int:group_id>/streaks', methods=['GET'])
def get_group_streaks(group_id):
    """Get streak information for all members of a group"""
    conn = sqlite3.connect('accountability.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT s.user_id, s.current_streak, s.longest_streak, s.last_activity,
                   u.username
            FROM streaks s
            JOIN users u ON s.user_id = u.id
            WHERE s.group_id = ?
            ORDER BY s.current_streak DESC, s.longest_streak DESC
        ''', (group_id,))
        
        streaks = cursor.fetchall()
        
        return jsonify([{
            'user_id': streak[0],
            'current_streak': streak[1],
            'longest_streak': streak[2],
            'last_activity': streak[3],
            'username': streak[4]
        } for streak in streaks])
    finally:
        conn.close()

# Streak management
@app.route('/api/streaks/<int:user_id>/update', methods=['POST'])
def update_streak(user_id):
    """Update user's streak after completing a study session"""
    data = request.get_json()
    group_id = data.get('group_id')
    
    success = dashboard_manager.update_streak(user_id, group_id)
    
    if success:
        return jsonify({'message': 'Streak updated successfully'}), 200
    else:
        return jsonify({'error': 'Failed to update streak'}), 500

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
