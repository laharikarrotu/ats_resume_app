# 🔑 OpenAI Integration Setup Guide

## ✅ What's Been Done

1. **Environment Variables Setup**
   - ✅ Added `.env` to `.gitignore` (your API key won't be committed)
   - ✅ Created `.env.example` (template for others)
   - ✅ Added `python-dotenv` to requirements.txt

2. **OpenAI Integration**
   - ✅ Created `src/llm_client.py` with full OpenAI integration
   - ✅ Updated `src/main.py` to use the new LLM client
   - ✅ Implemented keyword extraction using GPT-4o-mini
   - ✅ Added personalized bullet rewriting function
   - ✅ Added experience matching function

---

## 🚀 Next Steps (What You Need to Do)

### Step 1: Create `.env` File

Create a `.env` file in the project root (`ats_resume_app/.env`) with your OpenAI API key:

```bash
# .env file
OPENAI_API_KEY=sk-your-actual-api-key-here
```

**Important:** Replace `sk-your-actual-api-key-here` with your real OpenAI API key.

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- `openai` - OpenAI API client
- `python-dotenv` - Loads `.env` file
- All other dependencies

### Step 3: Test the Integration

Run the app:

```bash
uvicorn src.main:app --reload
```

Then:
1. Visit `http://127.0.0.1:8000`
2. Paste a job description
3. Click "Generate Resume"
4. The system will now use OpenAI to extract keywords!

---

## 🔍 How It Works

### Keyword Extraction
- Uses **GPT-4o-mini** (cost-effective model)
- Extracts 20-40 relevant keywords from job descriptions
- Returns structured list of skills, technologies, tools

### Fallback Behavior
- If OpenAI API key is not set → Uses basic keyword extraction (no API calls)
- If API call fails → Falls back to basic extraction
- App will still work without OpenAI (just less accurate)

### New Functions Available

1. **`extract_keywords(job_description: str)`**
   - Extracts keywords using OpenAI
   - Returns list of keywords

2. **`rewrite_experience_bullets(experience, job_description, keywords)`**
   - Rewrites your experience bullets to match job description
   - Uses STAR format
   - Injects relevant keywords naturally

3. **`match_experience_with_jd(experiences, job_description, top_n=3)`**
   - Prioritizes most relevant work experiences
   - Returns top N experiences for the resume

---

## 🧪 Testing

### Test Keyword Extraction

```python
from src.llm_client import extract_keywords

jd = "Looking for a Python developer with FastAPI, Docker, and AWS experience..."
keywords = extract_keywords(jd)
print(keywords)
# Should output: ['Python', 'FastAPI', 'Docker', 'AWS', ...]
```

### Test with API

```bash
curl -X POST "http://localhost:8000/api/generate_resume" \
  -H "Content-Type: application/json" \
  -d '{
    "job_description": "Looking for a Full-Stack Developer with React and Node.js..."
  }'
```

---

## ⚠️ Important Notes

1. **API Key Security**
   - Never commit `.env` file to git (already in `.gitignore`)
   - Don't share your API key publicly
   - Use `.env.example` as a template for others

2. **Cost Management**
   - Using `gpt-4o-mini` (cheapest option)
   - Each keyword extraction: ~$0.001-0.002
   - Each bullet rewrite: ~$0.002-0.005
   - Monitor usage at: https://platform.openai.com/usage

3. **Rate Limits**
   - OpenAI has rate limits (check your plan)
   - If you hit limits, the app falls back to basic extraction

---

## 🐛 Troubleshooting

### "OpenAI API error" in console
- Check your API key is correct in `.env`
- Verify you have credits in your OpenAI account
- Check internet connection

### "OPENAI_API_KEY not set"
- Make sure `.env` file exists in project root
- Verify the key is named exactly `OPENAI_API_KEY`
- Restart the server after creating `.env`

### App works but uses basic extraction
- Check console for error messages
- Verify API key format (should start with `sk-`)
- Check OpenAI account has available credits

---

## ✅ Integration Complete!

Once you've:
1. ✅ Created `.env` with your API key
2. ✅ Installed dependencies (`pip install -r requirements.txt`)
3. ✅ Started the server (`uvicorn src.main:app --reload`)

The app will automatically use OpenAI for keyword extraction!

**Next Steps:** We'll integrate this with resume parsing and personalized generation in the next steps.

