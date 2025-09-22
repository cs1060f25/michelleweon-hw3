"""
Google Calendar and iCal integration for StudyStreak
Handles calendar synchronization and smart scheduling
"""

import os
import json
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import requests
from typing import List, Dict, Optional

# Scopes for Google Calendar API
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly', 'https://www.googleapis.com/auth/calendar.events']

class CalendarIntegration:
    def __init__(self):
        self.google_service = None
        self.credentials = None
        
    def authenticate_google(self, credentials_file: str = 'credentials.json') -> bool:
        """Authenticate with Google Calendar API"""
        try:
            if os.path.exists('token.json'):
                self.credentials = Credentials.from_authorized_user_file('token.json', SCOPES)
            
            if not self.credentials or not self.credentials.valid:
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    self.credentials.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
                    self.credentials = flow.run_local_server(port=0)
                
                # Save credentials for next run
                with open('token.json', 'w') as token:
                    token.write(self.credentials.to_json())
            
            self.google_service = build('calendar', 'v3', credentials=self.credentials)
            return True
        except Exception as e:
            print(f"Google Calendar authentication failed: {e}")
            return False
    
    def get_google_events(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Fetch events from Google Calendar"""
        if not self.google_service:
            return []
        
        try:
            events_result = self.google_service.events().list(
                calendarId='primary',
                timeMin=start_time.isoformat() + 'Z',
                timeMax=end_time.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            return [{
                'title': event.get('summary', 'No Title'),
                'start': event['start'].get('dateTime', event['start'].get('date')),
                'end': event['end'].get('dateTime', event['end'].get('date')),
                'description': event.get('description', ''),
                'source': 'google'
            } for event in events]
        except Exception as e:
            print(f"Error fetching Google Calendar events: {e}")
            return []
    
    def parse_ical_url(self, ical_url: str, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Parse iCal URL and extract events"""
        try:
            response = requests.get(ical_url, timeout=10)
            response.raise_for_status()
            
            # Simple iCal parsing - in production, use icalendar library
            events = []
            lines = response.text.split('\n')
            current_event = {}
            
            for line in lines:
                line = line.strip()
                if line == 'BEGIN:VEVENT':
                    current_event = {}
                elif line == 'END:VEVENT':
                    if current_event:
                        events.append(current_event)
                    current_event = {}
                elif line.startswith('SUMMARY:'):
                    current_event['title'] = line[8:]
                elif line.startswith('DTSTART:'):
                    current_event['start'] = line[8:]
                elif line.startswith('DTEND:'):
                    current_event['end'] = line[6:]
                elif line.startswith('DESCRIPTION:'):
                    current_event['description'] = line[12:]
            
            # Filter events by date range
            filtered_events = []
            for event in events:
                if 'start' in event:
                    try:
                        event_start = datetime.fromisoformat(event['start'].replace('Z', '+00:00'))
                        if start_time <= event_start <= end_time:
                            event['source'] = 'ical'
                            filtered_events.append(event)
                    except:
                        continue
            
            return filtered_events
        except Exception as e:
            print(f"Error parsing iCal URL: {e}")
            return []
    
    def create_google_event(self, title: str, description: str, start_time: datetime, 
                           end_time: datetime, calendar_id: str = 'primary') -> Dict:
        """Create an event in Google Calendar"""
        if not self.google_service:
            raise Exception("Google Calendar not authenticated")
        
        event = {
            'summary': title,
            'description': description,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': 'America/Los_Angeles',  # Default timezone, can be made configurable
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'America/Los_Angeles',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                    {'method': 'popup', 'minutes': 30},       # 30 minutes before
                ],
            },
            'colorId': '2',  # Green color for study sessions
        }
        
        try:
            created_event = self.google_service.events().insert(
                calendarId=calendar_id, 
                body=event
            ).execute()
            
            return {
                'id': created_event['id'],
                'title': created_event['summary'],
                'start': created_event['start']['dateTime'],
                'end': created_event['end']['dateTime'],
                'htmlLink': created_event.get('htmlLink', ''),
                'source': 'google'
            }
        except Exception as e:
            raise Exception(f"Failed to create Google Calendar event: {e}")
    
    def get_all_events(self, ical_urls: List[str], start_time: datetime, end_time: datetime) -> List[Dict]:
        """Get events from all connected calendars"""
        all_events = []
        
        # Get Google Calendar events
        google_events = self.get_google_events(start_time, end_time)
        all_events.extend(google_events)
        
        # Get iCal events
        for ical_url in ical_urls:
            ical_events = self.parse_ical_url(ical_url, start_time, end_time)
            all_events.extend(ical_events)
        
        return all_events

class SmartScheduler:
    def __init__(self, calendar_integration: CalendarIntegration):
        self.calendar = calendar_integration
    
    def find_optimal_study_times(self, 
                                user_preferences: Dict,
                                study_duration: int = 120,  # minutes
                                days_ahead: int = 7) -> List[Dict]:
        """Find optimal study times based on preferences and existing calendar events"""
        
        start_time = datetime.now()
        end_time = start_time + timedelta(days=days_ahead)
        
        # Get existing events
        existing_events = self.calendar.get_all_events(
            user_preferences.get('ical_urls', []),
            start_time,
            end_time
        )
        
        # Convert events to datetime objects for easier comparison
        busy_times = []
        for event in existing_events:
            try:
                event_start = datetime.fromisoformat(event['start'].replace('Z', '+00:00'))
                event_end = datetime.fromisoformat(event['end'].replace('Z', '+00:00'))
                busy_times.append((event_start, event_end))
            except:
                continue
        
        # Get preferred study times from user preferences
        preferred_hours = user_preferences.get('preferred_study_hours', [9, 14, 19])
        preferred_days = user_preferences.get('preferred_days', [0, 1, 2, 3, 4])  # Monday-Friday
        
        # Find available slots
        available_slots = []
        
        for day_offset in range(days_ahead):
            current_date = start_time + timedelta(days=day_offset)
            
            # Skip if not a preferred day
            if current_date.weekday() not in preferred_days:
                continue
            
            for hour in preferred_hours:
                slot_start = current_date.replace(hour=hour, minute=0, second=0, microsecond=0)
                slot_end = slot_start + timedelta(minutes=study_duration)
                
                # Check if this slot conflicts with existing events
                conflicts = False
                for busy_start, busy_end in busy_times:
                    if (slot_start < busy_end and slot_end > busy_start):
                        conflicts = True
                        break
                
                if not conflicts:
                    available_slots.append({
                        'start_time': slot_start.isoformat(),
                        'end_time': slot_end.isoformat(),
                        'duration_minutes': study_duration,
                        'confidence_score': self._calculate_confidence_score(slot_start, user_preferences),
                        'subject': self._suggest_subject(slot_start, user_preferences)
                    })
        
        # Sort by confidence score and return top recommendations
        available_slots.sort(key=lambda x: x['confidence_score'], reverse=True)
        return available_slots[:10]  # Return top 10 recommendations
    
    def _calculate_confidence_score(self, slot_time: datetime, preferences: Dict) -> float:
        """Calculate confidence score for a study slot based on user preferences"""
        score = 0.0
        
        # Time of day preference
        hour = slot_time.hour
        if 6 <= hour <= 9:  # Morning
            score += preferences.get('morning_preference', 0.8)
        elif 10 <= hour <= 14:  # Midday
            score += preferences.get('midday_preference', 0.6)
        elif 15 <= hour <= 18:  # Afternoon
            score += preferences.get('afternoon_preference', 0.7)
        else:  # Evening
            score += preferences.get('evening_preference', 0.5)
        
        # Day of week preference
        weekday = slot_time.weekday()
        if weekday in preferences.get('preferred_days', [0, 1, 2, 3, 4]):
            score += 0.2
        
        # Avoid scheduling too close to existing events
        # This would require checking against calendar events
        
        return min(score, 1.0)
    
    def _suggest_subject(self, slot_time: datetime, preferences: Dict) -> str:
        """Suggest a subject based on time and user preferences"""
        subjects = preferences.get('subjects', ['General Study', 'Math', 'Science', 'Literature'])
        
        # Simple rotation based on day of week
        day_index = slot_time.weekday()
        return subjects[day_index % len(subjects)]
    
    def suggest_study_sessions_from_work(self, work_description: str, preferences: Dict) -> List[Dict]:
        """AI-powered study session suggestions based on work description"""
        # Parse work description to extract key information
        work_lower = work_description.lower()
        
        # Determine study type and duration based on keywords
        study_type = "General Study"
        duration = 120  # Default 2 hours
        
        if any(word in work_lower for word in ['pset', 'problem set', 'homework', 'assignment']):
            study_type = "Problem Set"
            duration = 180  # 3 hours for problem sets
        elif any(word in work_lower for word in ['exam', 'test', 'midterm', 'final']):
            study_type = "Exam Preparation"
            duration = 240  # 4 hours for exams
        elif any(word in work_lower for word in ['project', 'paper', 'essay', 'report']):
            study_type = "Project Work"
            duration = 200  # 3.5 hours for projects
        elif any(word in work_lower for word in ['read', 'reading', 'textbook', 'chapter']):
            study_type = "Reading & Notes"
            duration = 90   # 1.5 hours for reading
        elif any(word in work_lower for word in ['code', 'programming', 'debug', 'algorithm']):
            study_type = "Coding Practice"
            duration = 150  # 2.5 hours for coding
        
        # Extract subject from work description
        subject = "General"
        if any(word in work_lower for word in ['math', 'calculus', 'algebra', 'statistics']):
            subject = "Mathematics"
        elif any(word in work_lower for word in ['physics', 'chemistry', 'biology', 'science']):
            subject = "Science"
        elif any(word in work_lower for word in ['cs', 'computer science', 'programming', 'code']):
            subject = "Computer Science"
        elif any(word in work_lower for word in ['english', 'literature', 'writing', 'essay']):
            subject = "English/Literature"
        elif any(word in work_lower for word in ['history', 'social studies', 'politics']):
            subject = "History"
        
        # Generate study sessions based on work complexity
        sessions = []
        preferred_hours = preferences.get('preferred_study_hours', [9, 14, 19])
        
        # For complex work, suggest multiple sessions
        if duration > 180:
            # Split into multiple sessions
            session_duration = 120
            num_sessions = max(2, duration // session_duration)
            
            for i in range(num_sessions):
                hour = preferred_hours[i % len(preferred_hours)]
                start_time = datetime.now().replace(hour=hour, minute=0, second=0, microsecond=0) + timedelta(days=i)
                end_time = start_time + timedelta(minutes=session_duration)
                
                sessions.append({
                    'title': f"{study_type} - {subject} (Part {i+1})",
                    'description': f"Study session for: {work_description}",
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'duration_minutes': session_duration,
                    'subject': subject,
                    'type': study_type,
                    'confidence_score': 0.8
                })
        else:
            # Single session
            hour = preferred_hours[0]
            start_time = datetime.now().replace(hour=hour, minute=0, second=0, microsecond=0)
            end_time = start_time + timedelta(minutes=duration)
            
            sessions.append({
                'title': f"{study_type} - {subject}",
                'description': f"Study session for: {work_description}",
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration_minutes': duration,
                'subject': subject,
                'type': study_type,
                'confidence_score': 0.9
            })
        
        return sessions

# Example usage and testing
if __name__ == "__main__":
    # Initialize calendar integration
    calendar = CalendarIntegration()
    
    # Test Google Calendar authentication
    if calendar.authenticate_google():
        print("Google Calendar authentication successful!")
    else:
        print("Google Calendar authentication failed - using mock data")
    
    # Initialize smart scheduler
    scheduler = SmartScheduler(calendar)
    
    # Example user preferences
    user_prefs = {
        'preferred_study_hours': [9, 14, 19],
        'preferred_days': [0, 1, 2, 3, 4],  # Monday-Friday
        'morning_preference': 0.9,
        'midday_preference': 0.7,
        'afternoon_preference': 0.8,
        'evening_preference': 0.6,
        'subjects': ['Math', 'Physics', 'Chemistry', 'Literature', 'History'],
        'ical_urls': []  # Add iCal URLs here
    }
    
    # Get study recommendations
    recommendations = scheduler.find_optimal_study_times(user_prefs)
    
    print(f"\nFound {len(recommendations)} study time recommendations:")
    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec['subject']} - {rec['start_time']} to {rec['end_time']} (Score: {rec['confidence_score']:.2f})")
