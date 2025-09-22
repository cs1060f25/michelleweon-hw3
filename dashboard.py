"""
Dashboard functionality for StudyStreak
Handles user dashboard, streak tracking, and social features
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import calendar

class DashboardManager:
    def __init__(self, db_path: str = 'accountability.db'):
        self.db_path = db_path
    
    def get_user_dashboard(self, user_id: int) -> Dict:
        """Get comprehensive dashboard data for a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get user info
            cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            user = cursor.fetchone()
            if not user:
                return {'error': 'User not found'}
            
            # Get current streaks
            cursor.execute('''
                SELECT s.*, g.name as group_name
                FROM streaks s
                LEFT JOIN groups g ON s.group_id = g.id
                WHERE s.user_id = ?
            ''', (user_id,))
            streaks = cursor.fetchall()
            
            # Get recent study sessions
            cursor.execute('''
                SELECT * FROM study_sessions 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT 10
            ''', (user_id,))
            recent_sessions = cursor.fetchall()
            
            # Get groups user belongs to
            cursor.execute('''
                SELECT g.*, gm.joined_at
                FROM groups g
                JOIN group_members gm ON g.id = gm.group_id
                WHERE gm.user_id = ?
            ''', (user_id,))
            user_groups = cursor.fetchall()
            
            # Calculate statistics
            stats = self._calculate_user_stats(cursor, user_id)
            
            return {
                'user': {
                    'id': user[0],
                    'username': user[1],
                    'email': user[2],
                    'preferences': json.loads(user[3]) if user[3] else {}
                },
                'streaks': [{
                    'id': streak[0],
                    'user_id': streak[1],
                    'group_id': streak[2],
                    'current_streak': streak[3],
                    'longest_streak': streak[4],
                    'last_activity': streak[5],
                    'group_name': streak[7]
                } for streak in streaks],
                'recent_sessions': [{
                    'id': session[0],
                    'user_id': session[1],
                    'start_time': session[2],
                    'end_time': session[3],
                    'subject': session[4],
                    'completed': bool(session[5]),
                    'created_at': session[6]
                } for session in recent_sessions],
                'groups': [{
                    'id': group[0],
                    'name': group[1],
                    'description': group[2],
                    'created_by': group[3],
                    'created_at': group[4],
                    'joined_at': group[5]
                } for group in user_groups],
                'statistics': stats
            }
        finally:
            conn.close()
    
    def _calculate_user_stats(self, cursor, user_id: int) -> Dict:
        """Calculate user statistics"""
        # Total study sessions
        cursor.execute('SELECT COUNT(*) FROM study_sessions WHERE user_id = ?', (user_id,))
        total_sessions = cursor.fetchone()[0]
        
        # Completed sessions
        cursor.execute('SELECT COUNT(*) FROM study_sessions WHERE user_id = ? AND completed = 1', (user_id,))
        completed_sessions = cursor.fetchone()[0]
        
        # This week's sessions
        week_ago = datetime.now() - timedelta(days=7)
        cursor.execute('''
            SELECT COUNT(*) FROM study_sessions 
            WHERE user_id = ? AND created_at >= ?
        ''', (user_id, week_ago.isoformat()))
        this_week_sessions = cursor.fetchone()[0]
        
        # Current streak
        cursor.execute('''
            SELECT current_streak FROM streaks 
            WHERE user_id = ? 
            ORDER BY current_streak DESC 
            LIMIT 1
        ''', (user_id,))
        current_streak = cursor.fetchone()
        current_streak = current_streak[0] if current_streak else 0
        
        # Longest streak
        cursor.execute('''
            SELECT longest_streak FROM streaks 
            WHERE user_id = ? 
            ORDER BY longest_streak DESC 
            LIMIT 1
        ''', (user_id,))
        longest_streak = cursor.fetchone()
        longest_streak = longest_streak[0] if longest_streak else 0
        
        return {
            'total_sessions': total_sessions,
            'completed_sessions': completed_sessions,
            'completion_rate': (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0,
            'this_week_sessions': this_week_sessions,
            'current_streak': current_streak,
            'longest_streak': longest_streak
        }
    
    def update_streak(self, user_id: int, group_id: Optional[int] = None) -> bool:
        """Update user's streak after completing a study session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if streak exists
            cursor.execute('''
                SELECT id, current_streak, longest_streak 
                FROM streaks 
                WHERE user_id = ? AND group_id = ?
            ''', (user_id, group_id))
            
            streak = cursor.fetchone()
            now = datetime.now().isoformat()
            
            if streak:
                # Update existing streak
                new_streak = streak[1] + 1
                new_longest = max(streak[2], new_streak)
                
                cursor.execute('''
                    UPDATE streaks 
                    SET current_streak = ?, longest_streak = ?, last_activity = ?
                    WHERE id = ?
                ''', (new_streak, new_longest, now, streak[0]))
            else:
                # Create new streak
                cursor.execute('''
                    INSERT INTO streaks (user_id, group_id, current_streak, longest_streak, last_activity)
                    VALUES (?, ?, 1, 1, ?)
                ''', (user_id, group_id, now))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error updating streak: {e}")
            return False
        finally:
            conn.close()
    
    def get_group_leaderboard(self, group_id: int) -> List[Dict]:
        """Get leaderboard for a group"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT u.username, s.current_streak, s.longest_streak, s.last_activity
                FROM streaks s
                JOIN users u ON s.user_id = u.id
                WHERE s.group_id = ?
                ORDER BY s.current_streak DESC, s.longest_streak DESC
            ''', (group_id,))
            
            leaderboard = cursor.fetchall()
            
            return [{
                'username': row[0],
                'current_streak': row[1],
                'longest_streak': row[2],
                'last_activity': row[3],
                'rank': i + 1
            } for i, row in enumerate(leaderboard)]
        finally:
            conn.close()
    
    def get_weekly_progress(self, user_id: int, weeks: int = 4) -> List[Dict]:
        """Get weekly progress data for the last N weeks"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            weekly_data = []
            
            for week_offset in range(weeks):
                week_start = datetime.now() - timedelta(weeks=week_offset + 1)
                week_end = week_start + timedelta(days=7)
                
                # Get sessions for this week
                cursor.execute('''
                    SELECT COUNT(*), SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END)
                    FROM study_sessions 
                    WHERE user_id = ? AND created_at >= ? AND created_at < ?
                ''', (user_id, week_start.isoformat(), week_end.isoformat()))
                
                result = cursor.fetchone()
                total_sessions = result[0] or 0
                completed_sessions = result[1] or 0
                
                weekly_data.append({
                    'week': week_start.strftime('%Y-%m-%d'),
                    'total_sessions': total_sessions,
                    'completed_sessions': completed_sessions,
                    'completion_rate': (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0
                })
            
            return list(reversed(weekly_data))  # Return in chronological order
        finally:
            conn.close()
    
    def create_study_challenge(self, group_id: int, challenge_data: Dict) -> bool:
        """Create a study challenge for a group"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Create challenges table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS challenges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id INTEGER,
                    title TEXT NOT NULL,
                    description TEXT,
                    target_streak INTEGER,
                    start_date TIMESTAMP,
                    end_date TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (group_id) REFERENCES groups (id)
                )
            ''')
            
            cursor.execute('''
                INSERT INTO challenges (group_id, title, description, target_streak, start_date, end_date)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                group_id,
                challenge_data['title'],
                challenge_data.get('description', ''),
                challenge_data['target_streak'],
                challenge_data['start_date'],
                challenge_data['end_date']
            ))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error creating challenge: {e}")
            return False
        finally:
            conn.close()

class HabitTracker:
    def __init__(self, db_path: str = 'accountability.db'):
        self.db_path = db_path
        self.habit_formation_days = 70  # Target for habit formation
    
    def track_habit_progress(self, user_id: int) -> Dict:
        """Track progress towards habit formation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get user's study sessions
            cursor.execute('''
                SELECT created_at, completed 
                FROM study_sessions 
                WHERE user_id = ? 
                ORDER BY created_at ASC
            ''', (user_id,))
            
            sessions = cursor.fetchall()
            
            if not sessions:
                return {
                    'days_completed': 0,
                    'days_remaining': self.habit_formation_days,
                    'progress_percentage': 0,
                    'current_streak': 0,
                    'is_on_track': False
                }
            
            # Calculate consecutive days
            current_streak = 0
            last_date = None
            
            for session in sessions:
                session_date = datetime.fromisoformat(session[0]).date()
                if session[1]:  # If completed
                    if last_date is None or session_date == last_date + timedelta(days=1):
                        current_streak += 1
                    elif session_date != last_date:
                        current_streak = 1
                    last_date = session_date
            
            days_completed = min(current_streak, self.habit_formation_days)
            days_remaining = max(0, self.habit_formation_days - days_completed)
            progress_percentage = (days_completed / self.habit_formation_days) * 100
            
            return {
                'days_completed': days_completed,
                'days_remaining': days_remaining,
                'progress_percentage': progress_percentage,
                'current_streak': current_streak,
                'is_on_track': current_streak >= 5,  # Consider on track if 5+ day streak
                'milestone_reached': days_completed >= self.habit_formation_days
            }
        finally:
            conn.close()
    
    def get_milestone_rewards(self, progress: Dict) -> List[str]:
        """Get milestone rewards based on progress"""
        rewards = []
        
        if progress['current_streak'] >= 7:
            rewards.append("🔥 7-day streak! You're building momentum!")
        
        if progress['current_streak'] >= 21:
            rewards.append("🌟 21-day streak! This is becoming a habit!")
        
        if progress['current_streak'] >= 30:
            rewards.append("💪 30-day streak! You're unstoppable!")
        
        if progress['days_completed'] >= 50:
            rewards.append("🎯 50 days! You're almost at the finish line!")
        
        if progress['milestone_reached']:
            rewards.append("🏆 Congratulations! You've formed a lasting habit!")
        
        return rewards

# Example usage
if __name__ == "__main__":
    dashboard = DashboardManager()
    habit_tracker = HabitTracker()
    
    # Example: Get dashboard for user 1
    user_dashboard = dashboard.get_user_dashboard(1)
    print("User Dashboard:", json.dumps(user_dashboard, indent=2, default=str))
    
    # Example: Track habit progress
    habit_progress = habit_tracker.track_habit_progress(1)
    print("\nHabit Progress:", habit_progress)
    
    # Example: Get milestone rewards
    rewards = habit_tracker.get_milestone_rewards(habit_progress)
    print("\nMilestone Rewards:", rewards)
