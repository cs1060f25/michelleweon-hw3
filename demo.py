#!/usr/bin/env python3
"""
Demo script for StudyStreak
Demonstrates key features of the accountability tool
"""

import requests
import json
from datetime import datetime, timedelta

# Base URL for the API
BASE_URL = "http://localhost:5000"

def demo_studystreak():
    """Run a comprehensive demo of StudyStreak features"""
    print("🔥 StudyStreak Demo - Building Productive Habits Together! 🔥\n")
    
    # 1. Create a user
    print("1. Creating a new user...")
    user_data = {
        "username": "demo_student",
        "email": "demo@studystreak.com",
        "preferences": {
            "preferred_study_hours": [9, 14, 19],
            "preferred_days": [0, 1, 2, 3, 4],  # Monday-Friday
            "morning_preference": 0.9,
            "subjects": ["Mathematics", "Physics", "Chemistry", "Literature"]
        }
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/users", json=user_data)
        if response.status_code == 201:
            user = response.json()
            print(f"✅ User created: {user['username']} (ID: {user['id']})")
            user_id = user['id']
        else:
            print(f"❌ Failed to create user: {response.text}")
            return
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the server. Make sure to run 'python app.py' first!")
        return
    
    # 2. Create a study group
    print("\n2. Creating a study group...")
    group_data = {
        "name": "Schoova Study Squad",
        "description": "A group for Schoova users to stay accountable and build study habits together",
        "created_by": user_id
    }
    
    response = requests.post(f"{BASE_URL}/api/groups", json=group_data)
    if response.status_code == 201:
        group = response.json()
        print(f"✅ Group created: {group['name']} (ID: {group['id']})")
        group_id = group['id']
    else:
        print(f"❌ Failed to create group: {response.text}")
        return
    
    # 2.5. Test getting all groups
    print("\n2.5. Testing group listing...")
    response = requests.get(f"{BASE_URL}/api/groups")
    if response.status_code == 200:
        groups = response.json()
        print(f"✅ Found {len(groups)} groups available")
        for group in groups:
            print(f"   - {group['name']}: {group['description']}")
    else:
        print(f"❌ Failed to get groups: {response.text}")
    
    # 3. Get smart schedule recommendations
    print("\n3. Getting smart schedule recommendations...")
    schedule_data = {
        "user_id": user_id,
        "preferences": {}
    }
    
    response = requests.post(f"{BASE_URL}/api/schedule/recommend", json=schedule_data)
    if response.status_code == 200:
        recommendations = response.json()
        print(f"✅ Found {len(recommendations['recommended_sessions'])} study time recommendations:")
        for i, session in enumerate(recommendations['recommended_sessions'][:3], 1):
            start_time = datetime.fromisoformat(session['start_time'])
            end_time = datetime.fromisoformat(session['end_time'])
            print(f"   {i}. {session['subject']} - {start_time.strftime('%A %I:%M %p')} to {end_time.strftime('%I:%M %p')}")
    else:
        print(f"❌ Failed to get recommendations: {response.text}")
    
    # 4. Create and complete study sessions
    print("\n4. Creating study sessions...")
    subjects = ["Mathematics", "Physics", "Chemistry"]
    
    for i, subject in enumerate(subjects):
        start_time = datetime.now() + timedelta(hours=i*2)
        end_time = start_time + timedelta(hours=2)
        
        session_data = {
            "user_id": user_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "subject": subject
        }
        
        response = requests.post(f"{BASE_URL}/api/study-sessions", json=session_data)
        if response.status_code == 201:
            session = response.json()
            print(f"✅ Created {subject} session (ID: {session['id']})")
            
            # Complete the session
            complete_response = requests.put(f"{BASE_URL}/api/study-sessions/{session['id']}/complete")
            if complete_response.status_code == 200:
                print(f"   ✅ Completed {subject} session")
                
                # Update streak
                streak_data = {"group_id": group_id}
                streak_response = requests.post(f"{BASE_URL}/api/streaks/{user_id}/update", json=streak_data)
                if streak_response.status_code == 200:
                    print(f"   🔥 Streak updated!")
        else:
            print(f"❌ Failed to create {subject} session: {response.text}")
    
    # 5. Get dashboard data
    print("\n5. Getting dashboard data...")
    response = requests.get(f"{BASE_URL}/api/dashboard/{user_id}")
    if response.status_code == 200:
        dashboard = response.json()
        print("✅ Dashboard data retrieved:")
        print(f"   📊 Total sessions: {dashboard['statistics']['total_sessions']}")
        print(f"   ✅ Completed sessions: {dashboard['statistics']['completed_sessions']}")
        print(f"   📈 Completion rate: {dashboard['statistics']['completion_rate']:.1f}%")
        print(f"   🔥 Current streak: {dashboard['statistics']['current_streak']}")
    else:
        print(f"❌ Failed to get dashboard: {response.text}")
    
    # 6. Get habit progress
    print("\n6. Checking habit formation progress...")
    response = requests.get(f"{BASE_URL}/api/dashboard/{user_id}/habit-progress")
    if response.status_code == 200:
        habit_data = response.json()
        progress = habit_data['progress']
        rewards = habit_data['rewards']
        
        print("✅ Habit progress:")
        print(f"   📅 Days completed: {progress['days_completed']}/70")
        print(f"   📊 Progress: {progress['progress_percentage']:.1f}%")
        print(f"   🔥 Current streak: {progress['current_streak']} days")
        print(f"   🎯 On track: {'Yes' if progress['is_on_track'] else 'No'}")
        
        if rewards:
            print("   🏆 Milestone rewards:")
            for reward in rewards:
                print(f"      {reward}")
    else:
        print(f"❌ Failed to get habit progress: {response.text}")
    
    # 7. Get group leaderboard
    print("\n7. Getting group leaderboard...")
    response = requests.get(f"{BASE_URL}/api/groups/{group_id}/leaderboard")
    if response.status_code == 200:
        leaderboard = response.json()
        print("✅ Group leaderboard:")
        for i, member in enumerate(leaderboard, 1):
            print(f"   {i}. {member['username']} - {member['current_streak']} day streak")
    else:
        print(f"❌ Failed to get leaderboard: {response.text}")
    
    print("\n🎉 Demo completed! StudyStreak is helping you build productive habits!")
    print("\nKey Features Demonstrated:")
    print("✅ User registration and preferences")
    print("✅ Study group creation and management")
    print("✅ Smart schedule recommendations")
    print("✅ Study session tracking and completion")
    print("✅ Streak tracking and social accountability")
    print("✅ Habit formation progress monitoring")
    print("✅ Group leaderboards and competition")
    
    print("\n🚀 Next Steps:")
    print("1. Run 'python app.py' to start the server")
    print("2. Visit http://localhost:5000 to see the web interface")
    print("3. Set up Google Calendar integration for full functionality")
    print("4. Invite friends to join your study groups!")

if __name__ == "__main__":
    demo_studystreak()
