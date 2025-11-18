# 🚂 Railway Deployment Guide

## ✅ **Why Railway is Perfect for This App**

- ✅ **No timeout limits** - LLM calls can take as long as needed
- ✅ **Full file system access** - No restrictions on file operations
- ✅ **Auto-deploys on git push** - Automatic deployments
- ✅ **Easy environment variables** - Simple configuration
- ✅ **Free tier available** - $5 credit/month
- ✅ **Works with your current code** - No modifications needed!

---

## 🚀 **Step-by-Step Railway Setup**

### **Step 1: Create Railway Account**

1. Go to https://railway.app
2. Click **"Start a New Project"**
3. Sign up with **GitHub** (recommended - easier integration)
4. Authorize Railway to access your GitHub

### **Step 2: Deploy from GitHub**

1. After signing in, click **"New Project"**
2. Select **"Deploy from GitHub repo"**
3. Find and select your `ats_resume_app` repository
4. Click **"Deploy Now"**

Railway will automatically:
- Detect it's a Python project
- Install dependencies from `requirements.txt`
- Start the app using the `Procfile` or auto-detect

### **Step 3: Configure Environment Variables**

1. In your Railway project dashboard, click on your service
2. Go to **"Variables"** tab
3. Click **"New Variable"**
4. Add:
   - **Name:** `OPENAI_API_KEY`
   - **Value:** `sk-your-actual-api-key-here`
5. Click **"Add"**

Railway will automatically redeploy when you add variables.

### **Step 4: Get Your App URL**

1. In Railway dashboard, click on your service
2. Go to **"Settings"** tab
3. Scroll to **"Domains"** section
4. Railway automatically generates a domain like: `your-app.railway.app`
5. Click on the domain to open your app!

---

## ⚙️ **Railway Configuration (Optional)**

The `railway.json` file is already created with optimal settings:

```json
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "uvicorn src.main:app --host 0.0.0.0 --port $PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

This tells Railway:
- Use Nixpacks builder (auto-detects Python)
- Start command for FastAPI
- Auto-restart on failure

**You don't need to change anything** - it's already configured!

---

## 🔍 **Verify Deployment**

### **Test Your App:**

1. Visit your Railway URL: `https://your-app.railway.app`
2. Test the health endpoint: `https://your-app.railway.app/health`
3. Try uploading a resume
4. Try generating a resume

### **Check Logs:**

1. In Railway dashboard → Your service
2. Click **"Deployments"** tab
3. Click on the latest deployment
4. View **"Logs"** to see what's happening

---

## 🔄 **Auto-Deploy Setup**

Railway automatically deploys when you push to GitHub:

1. **Make changes locally**
2. **Commit and push:**
   ```bash
   git add .
   git commit -m "Your changes"
   git push
   ```
3. **Railway automatically:**
   - Detects the push
   - Builds your app
   - Deploys the new version
   - Updates your live app

**No manual deployment needed!**

---

## 💰 **Railway Pricing**

### **Free Tier:**
- $5 credit/month
- Enough for moderate usage
- Perfect for testing and small projects

### **Pro Tier:**
- $20/month
- More resources
- Better performance
- For production apps

**For this app, free tier should be sufficient!**

---

## 🐛 **Troubleshooting**

### **App Not Starting:**

1. **Check Logs:**
   - Railway Dashboard → Service → Deployments → Logs
   - Look for error messages

2. **Common Issues:**
   - Missing `OPENAI_API_KEY` → Add it in Variables
   - Port not set → Railway sets `$PORT` automatically
   - Dependencies not installing → Check `requirements.txt`

### **Environment Variables Not Working:**

1. Make sure variable is set in Railway dashboard
2. Redeploy after adding variables
3. Check variable name matches exactly (case-sensitive)

### **File Upload Issues:**

- Railway has full file system access
- Files are stored in the container
- Should work without issues

---

## 📊 **Monitoring**

### **View Metrics:**

1. Railway Dashboard → Your Service
2. **"Metrics"** tab shows:
   - CPU usage
   - Memory usage
   - Network traffic
   - Request count

### **View Logs:**

1. **"Deployments"** tab → Latest deployment → **"Logs"**
2. Real-time logs available
3. Search and filter logs

---

## 🔒 **Security Best Practices**

1. **Never commit API keys:**
   - ✅ Already in `.gitignore`
   - ✅ Use Railway Variables

2. **Use HTTPS:**
   - ✅ Railway provides HTTPS automatically

3. **Monitor Usage:**
   - Check Railway dashboard regularly
   - Monitor API costs (OpenAI)

---

## ✅ **Deployment Checklist**

Before deploying, ensure:

- [x] Code is pushed to GitHub
- [ ] Railway account created
- [ ] Project connected to GitHub repo
- [ ] `OPENAI_API_KEY` environment variable added
- [ ] App URL is working
- [ ] Health check passes: `/health`
- [ ] Can upload resume
- [ ] Can generate resume

---

## 🎉 **You're All Set!**

Once deployed on Railway:

1. ✅ Your app is live at `https://your-app.railway.app`
2. ✅ Auto-deploys on every git push
3. ✅ Full file system access
4. ✅ No timeout limits
5. ✅ Easy to monitor and debug

**Share your app URL and start generating resumes!**

---

## 📚 **Additional Resources**

- **Railway Docs:** https://docs.railway.app
- **Railway Discord:** https://discord.gg/railway
- **Railway Status:** https://status.railway.app

---

**Happy deploying! 🚂**

