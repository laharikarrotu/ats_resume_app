# 📦 GitHub Setup Guide

## 🚀 Quick Start

### **Step 1: Initialize Git (if not already done)**

```bash
# Check if git is initialized
git status

# If not initialized, run:
git init
```

### **Step 2: Create GitHub Repository**

1. **Go to GitHub:**
   - Visit https://github.com/new
   - Or click the "+" icon → "New repository"

2. **Repository Settings:**
   - **Repository name:** `ats_resume_app`
   - **Description:** `AI-Powered ATS Resume Generator with OpenAI Integration`
   - **Visibility:** Choose Public or Private
   - **⚠️ IMPORTANT:** Do NOT check "Initialize with README" (we already have one)
   - Click "Create repository"

### **Step 3: Connect Local Repository to GitHub**

```bash
# Add remote (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/ats_resume_app.git

# Verify remote was added
git remote -v
```

### **Step 4: Stage and Commit All Files**

```bash
# Stage all files
git add .

# Create initial commit
git commit -m "Initial commit: ATS Resume Generator with OpenAI integration, resume parsing, and personalized generation"

# If you get an error about user.name or user.email, set them first:
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

### **Step 5: Push to GitHub**

```bash
# Rename branch to main (if needed)
git branch -M main

# Push to GitHub
git push -u origin main
```

**If prompted for credentials:**
- Use GitHub Personal Access Token (not password)
- Create token: GitHub → Settings → Developer settings → Personal access tokens → Generate new token
- Select scopes: `repo` (full control)

---

## ✅ **Verify Setup**

1. **Check GitHub:**
   - Visit: `https://github.com/YOUR_USERNAME/ats_resume_app`
   - You should see all your files

2. **Verify .gitignore:**
   - Make sure `.env` is NOT visible on GitHub
   - Make sure `outputs/` and `uploads/` are NOT visible

---

## 🔄 **Future Updates**

### **Making Changes and Pushing:**

```bash
# 1. Check status
git status

# 2. Stage changes
git add .

# 3. Commit with descriptive message
git commit -m "Description of your changes"

# 4. Push to GitHub
git push
```

### **Good Commit Messages:**

```bash
git commit -m "Add resume upload functionality"
git commit -m "Improve UI accessibility"
git commit -m "Fix OpenAI API error handling"
git commit -m "Update deployment configuration"
```

---

## 🌿 **Branching Strategy (Optional)**

### **Create Feature Branch:**

```bash
# Create and switch to new branch
git checkout -b feature/new-feature

# Make changes, then commit
git add .
git commit -m "Add new feature"

# Push branch to GitHub
git push -u origin feature/new-feature

# Merge to main (on GitHub or locally)
git checkout main
git merge feature/new-feature
git push
```

---

## 🔒 **Security Checklist**

Before pushing, ensure:

- [ ] ✅ `.env` is in `.gitignore` (already done)
- [ ] ✅ No API keys in code
- [ ] ✅ `outputs/` and `uploads/` are ignored
- [ ] ✅ No sensitive data in commits

**If you accidentally committed secrets:**
```bash
# Remove from git history (use with caution!)
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env" \
  --prune-empty --tag-name-filter cat -- --all

# Force push (warning: rewrites history)
git push origin --force --all
```

---

## 📝 **Repository Structure on GitHub**

Your GitHub repo should have:

```
ats_resume_app/
├── .gitignore          ✅
├── README.md           ✅
├── requirements.txt    ✅
├── Dockerfile          ✅
├── vercel.json         ✅ (for Vercel)
├── Procfile            ✅ (for Heroku/Render)
├── runtime.txt         ✅ (for some platforms)
├── DEPLOYMENT.md       ✅
├── src/
│   ├── main.py
│   ├── resume_generator.py
│   ├── resume_parser.py
│   ├── llm_client.py
│   ├── models.py
│   └── utils.py
├── templates/
│   └── index.html
├── static/
│   └── styles.css
└── resume_templates/
    └── README_PLACEHOLDER.md
```

**Should NOT have:**
- ❌ `.env` file
- ❌ `outputs/` directory
- ❌ `uploads/` directory
- ❌ `__pycache__/` directories
- ❌ `venv/` or `.venv/` directories

---

## 🎯 **Next Steps After GitHub Setup**

1. **Connect to Deployment Platform:**
   - Railway: Connect GitHub repo
   - Render: Connect GitHub repo
   - Vercel: Import GitHub repo

2. **Set Environment Variables:**
   - Add `OPENAI_API_KEY` in platform settings
   - Never commit API keys to GitHub!

3. **Enable Auto-Deploy:**
   - Most platforms auto-deploy on `git push`
   - Test by making a small change and pushing

---

## 🆘 **Troubleshooting**

### **"Repository not found" error:**
- Check repository name matches
- Verify you have access to the repo
- Check remote URL: `git remote -v`

### **"Permission denied" error:**
- Use Personal Access Token instead of password
- Check token has `repo` scope

### **"Large file" error:**
- GitHub has 100MB file limit
- Use Git LFS for large files
- Or add large files to `.gitignore`

---

## ✅ **You're All Set!**

Once your code is on GitHub, you can:
- ✅ Share with others
- ✅ Deploy to cloud platforms
- ✅ Track changes
- ✅ Collaborate
- ✅ Showcase your work

**Happy coding! 🚀**

