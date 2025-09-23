# Schoova Deployment Guide

## Vercel Deployment Steps

### 1. Prerequisites
- Install Vercel CLI: `npm i -g vercel`
- Make sure you're in the project directory: `/Users/michelleweon/Desktop/f25/cs1060/michelleweon-hw3`

### 2. Deploy to Vercel
```bash
# Login to Vercel (if not already logged in)
vercel login

# Deploy the project
vercel

# Follow the prompts:
# - Set up and deploy? Yes
# - Which scope? (choose your account)
# - Link to existing project? No
# - Project name: schoova (or your preferred name)
# - Directory: ./
# - Override settings? No
```

### 3. Environment Variables (if needed)
If you need to set environment variables:
```bash
vercel env add FLASK_ENV production
vercel env add PYTHONPATH .
```

### 4. Troubleshooting 404 Errors

#### Common Causes:
1. **Missing dependencies**: Make sure `requirements.txt` is complete
2. **Import errors**: Check that all modules can be imported
3. **Database issues**: SQLite files might not persist on Vercel
4. **Route configuration**: Ensure `vercel.json` is correct

#### Debug Steps:
1. **Check build logs**: `vercel logs <deployment-url>`
2. **Test health endpoint**: Visit `https://your-app.vercel.app/health`
3. **Check function logs**: `vercel logs <function-id>`

#### Quick Fixes:
1. **Redeploy**: `vercel --prod`
2. **Clear cache**: `vercel --prod --force`
3. **Check file structure**: Ensure all files are in the root directory

### 5. Alternative Deployment Options

If Vercel continues to have issues, consider:

#### Railway
```bash
# Install Railway CLI
npm install -g @railway/cli

# Deploy
railway login
railway init
railway up
```

#### Heroku
```bash
# Install Heroku CLI
# Create Procfile
echo "web: python app.py" > Procfile

# Deploy
heroku create schoova-app
git add .
git commit -m "Deploy to Heroku"
git push heroku main
```

### 6. Local Testing
Before deploying, test locally:
```bash
python3 app.py
# Visit http://localhost:5000
# Test health endpoint: http://localhost:5000/health
```

### 7. Database Considerations
- SQLite files don't persist on Vercel
- Consider using a cloud database (PostgreSQL, MongoDB) for production
- For now, the app will create a new database on each deployment

## Current Status
✅ App imports successfully
✅ Health endpoint works
✅ All routes defined
✅ Vercel configuration updated
✅ Requirements.txt complete
