# 🚀 Deployment Guide

## 📦 **GitHub Setup**

### **Step 1: Initialize Git Repository**

```bash
# If not already initialized
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: ATS Resume Generator with OpenAI integration"

# Add remote repository (replace with your GitHub repo URL)
git remote add origin https://github.com/yourusername/ats_resume_app.git

# Push to GitHub
git branch -M main
git push -u origin main
```

### **Step 2: GitHub Repository Setup**

1. **Create New Repository on GitHub:**
   - Go to https://github.com/new
   - Repository name: `ats_resume_app`
   - Description: "AI-Powered ATS Resume Generator with OpenAI"
   - Choose Public or Private
   - **Don't** initialize with README (we already have one)

2. **Connect Local Repo:**
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/ats_resume_app.git
   git branch -M main
   git push -u origin main
   ```

---

## 🌐 **Deployment Options**

### **Option 1: Vercel (Serverless Functions)**

**Note:** Vercel works but is optimized for frontend. For FastAPI, consider Railway or Render (see below).

#### **Vercel Setup:**

1. **Install Vercel CLI:**
   ```bash
   npm install -g vercel
   ```

2. **Login to Vercel:**
   ```bash
   vercel login
   ```

3. **Deploy:**
   ```bash
   vercel
   ```

4. **Set Environment Variables:**
   - Go to Vercel Dashboard → Your Project → Settings → Environment Variables
   - Add: `OPENAI_API_KEY=sk-your-key-here`

5. **Redeploy after adding env vars:**
   ```bash
   vercel --prod
   ```

**Limitations:**
- ⚠️ Serverless functions have timeout limits (10s on free tier)
- ⚠️ File uploads might be limited
- ⚠️ Not ideal for long-running LLM operations

---

### **Option 2: Railway (Recommended for FastAPI) ⭐**

**Best for:** FastAPI applications with file uploads and LLM calls

#### **Railway Setup:**

1. **Create Railway Account:**
   - Go to https://railway.app
   - Sign up with GitHub

2. **Create New Project:**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your `ats_resume_app` repository

3. **Configure:**
   - Railway auto-detects Python
   - Add environment variable: `OPENAI_API_KEY` in Variables tab

4. **Deploy:**
   - Railway automatically deploys on git push
   - Get your app URL: `https://your-app.railway.app`

**Advantages:**
- ✅ Free tier available ($5 credit/month)
- ✅ Auto-deploys on git push
- ✅ Supports long-running processes (no timeout limits!)
- ✅ Easy environment variable management
- ✅ Full file system access
- ✅ Built-in PostgreSQL (if needed later)

**Railway Configuration:**
✅ `railway.json` is already created and configured!

**See [RAILWAY_SETUP.md](./RAILWAY_SETUP.md) for detailed step-by-step instructions.**

---

### **Option 3: Render (Also Great for FastAPI)**

#### **Render Setup:**

1. **Create Render Account:**
   - Go to https://render.com
   - Sign up with GitHub

2. **Create New Web Service:**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Choose branch: `main`

3. **Configure:**
   - **Name:** `ats-resume-generator`
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn src.main:app --host 0.0.0.0 --port $PORT`

4. **Environment Variables:**
   - Add: `OPENAI_API_KEY=sk-your-key-here`

5. **Deploy:**
   - Click "Create Web Service"
   - Render auto-deploys

**Advantages:**
- ✅ Free tier available (with limitations)
- ✅ Auto-deploys on git push
- ✅ Easy to use
- ✅ Good for FastAPI

---

### **Option 4: Fly.io (Good for Global Distribution)**

#### **Fly.io Setup:**

1. **Install Fly CLI:**
   ```bash
   # Windows (PowerShell)
   iwr https://fly.io/install.ps1 -useb | iex
   ```

2. **Login:**
   ```bash
   fly auth login
   ```

3. **Create App:**
   ```bash
   fly launch
   ```

4. **Set Secrets:**
   ```bash
   fly secrets set OPENAI_API_KEY=sk-your-key-here
   ```

5. **Deploy:**
   ```bash
   fly deploy
   ```

---

## 🔧 **Pre-Deployment Checklist**

### **Before Deploying:**

- [ ] **Environment Variables:**
  - [ ] `OPENAI_API_KEY` is set
  - [ ] No hardcoded secrets in code

- [ ] **Dependencies:**
  - [ ] `requirements.txt` is up to date
  - [ ] All packages are listed

- [ ] **Files:**
  - [ ] `.env` is in `.gitignore` ✅
  - [ ] `outputs/` and `uploads/` are in `.gitignore` ✅
  - [ ] No sensitive data in code

- [ ] **Configuration:**
  - [ ] `Dockerfile` is ready (if using Docker)
  - [ ] Port configuration uses `$PORT` environment variable

---

## 📝 **Update Code for Deployment**

### **1. Update main.py for Production**

The current code should work, but you might want to add:

```python
import os

# Use PORT from environment (for cloud platforms)
PORT = int(os.getenv("PORT", 8000))

# Update uvicorn command in Dockerfile or platform config
# CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", str(PORT)]
```

### **2. Create runtime.txt (for some platforms)**

```txt
python-3.11.0
```

### **3. Create Procfile (for Heroku/Render)**

```procfile
web: uvicorn src.main:app --host 0.0.0.0 --port $PORT
```

---

## 🚀 **Recommended: Railway Deployment**

**Why Railway:**
- ✅ Best for FastAPI
- ✅ Free tier
- ✅ Auto-deploys
- ✅ Easy setup

**Quick Start:**
1. Push code to GitHub
2. Connect Railway to GitHub repo
3. Add `OPENAI_API_KEY` environment variable
4. Deploy!

---

## 🔗 **Post-Deployment**

### **After Deployment:**

1. **Test Your App:**
   - Visit your deployment URL
   - Test resume upload
   - Test resume generation

2. **Update README:**
   - Add deployment URL
   - Update documentation

3. **Monitor:**
   - Check logs
   - Monitor errors
   - Track usage

---

## 📚 **Additional Resources**

- **Railway Docs:** https://docs.railway.app
- **Render Docs:** https://render.com/docs
- **Vercel Docs:** https://vercel.com/docs
- **Fly.io Docs:** https://fly.io/docs

---

**Ready to deploy? Choose your platform and follow the steps above!**

