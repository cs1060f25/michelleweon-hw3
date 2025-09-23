# 🚀 Schoova Deployment Guide

## Current Status
✅ App works locally  
✅ All dependencies installed  
✅ Database initializes correctly  
❌ Vercel deployment failing (404 error)

## 🎯 **Recommended Solution: Railway (Easiest)**

Railway is more reliable for Python Flask apps than Vercel.

### Step 1: Install Railway CLI
```bash
npm install -g @railway/cli
```

### Step 2: Deploy to Railway
```bash
cd /Users/michelleweon/Desktop/f25/cs1060/michelleweon-hw3
railway login
railway init
railway up
```

### Step 3: Get Your URL
Railway will give you a URL like: `https://schoova-production.up.railway.app`

---

## 🔧 **Alternative: Fix Vercel Deployment**

### Option A: Use the New API Structure
I've created `api/index.py` which should work better with Vercel:

```bash
# Try deploying again
vercel --prod
```

### Option B: Manual Vercel Setup
1. Go to [vercel.com](https://vercel.com)
2. Click "New Project"
3. Import your GitHub repository
4. Set build command: `python -m pip install -r requirements.txt`
5. Set output directory: `.`
6. Deploy

---

## 🌐 **Alternative: Heroku (Most Reliable)**

### Step 1: Create Procfile
```bash
echo "web: python app.py" > Procfile
```

### Step 2: Install Heroku CLI
```bash
# On macOS
brew install heroku/brew/heroku

# Or download from https://devcenter.heroku.com/articles/heroku-cli
```

### Step 3: Deploy
```bash
heroku login
heroku create schoova-app
git add .
git commit -m "Deploy to Heroku"
git push heroku main
```

---

## 🐳 **Alternative: Docker + Any Platform**

### Step 1: Create Dockerfile
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["python", "app.py"]
```

### Step 2: Deploy to any platform
- **Render**: Connect GitHub repo, auto-deploys
- **Fly.io**: `fly launch` then `fly deploy`
- **DigitalOcean**: Use App Platform

---

## 🔍 **Debugging Current Vercel Issue**

### Check Vercel Logs
```bash
vercel logs
```

### Common Vercel Issues:
1. **Python version mismatch** - Vercel uses Python 3.9
2. **Missing dependencies** - Check requirements.txt
3. **Import errors** - Some modules might not work on Vercel
4. **Database issues** - SQLite doesn't persist on Vercel

### Quick Vercel Fix
```bash
# Clear Vercel cache and redeploy
vercel --prod --force
```

---

## 🎯 **My Recommendation**

**Use Railway** - it's the most reliable for Python Flask apps:

1. `npm install -g @railway/cli`
2. `railway login`
3. `railway init`
4. `railway up`

Railway will:
- ✅ Auto-detect Python
- ✅ Install dependencies automatically
- ✅ Handle database persistence
- ✅ Give you a working URL immediately

---

## 🆘 **If All Else Fails**

**Local Development Server:**
```bash
cd /Users/michelleweon/Desktop/f25/cs1060/michelleweon-hw3
python3 app.py
# Visit http://localhost:5000
```

**Share via ngrok:**
```bash
# Install ngrok
brew install ngrok

# Run your app
python3 app.py

# In another terminal
ngrok http 5000
# This gives you a public URL like https://abc123.ngrok.io
```

---

## 📊 **Current App Features Working Locally:**
- ✅ User authentication (login/signup)
- ✅ Study group creation and joining
- ✅ Group accomplishments and streaks
- ✅ AI-powered study session suggestions
- ✅ Manual study session scheduling
- ✅ Google Calendar integration
- ✅ Interactive calendar view
- ✅ Dashboard with all features

The app is fully functional - we just need to get it deployed! 🚀
