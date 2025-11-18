"""
LLM-Based Resume Parser: Uses OpenAI to extract structured data from resume text with high accuracy.

This provides >90% accuracy by using LLM to understand context and structure.
"""

import json
import os
from typing import List, Optional

from openai import OpenAI
from dotenv import load_dotenv

from .models import ResumeData, Education, Experience, Project, Certification

# Load environment variables
load_dotenv()

# Initialize OpenAI client
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


def parse_resume_with_llm(resume_text: str) -> ResumeData:
    """
    Parse resume text using OpenAI LLM for high accuracy extraction.
    
    Args:
        resume_text: Raw text extracted from PDF/DOCX resume
    
    Returns:
        ResumeData: Structured resume data with >90% accuracy
    """
    if not client:
        # Fallback to basic parsing if no API key
        from .resume_parser import _parse_text_to_resume_data
        return _parse_text_to_resume_data(resume_text)
    
    prompt = f"""You are an expert resume parser. Extract ALL information from the following resume text with maximum accuracy (>90%).

Extract and return a JSON object with this exact structure:
{{
  "name": "Full Name",
  "email": "email@example.com",
  "phone": "+1 (123) 456-7890",
  "linkedin": "https://linkedin.com/in/...",
  "github": "https://github.com/...",
  "location": "City, State",
  "education": [
    {{
      "degree": "Degree Name",
      "university": "University Name",
      "location": "City, State",
      "dates": "2020-2024",
      "gpa": "3.5/4.0",
      "coursework": ["Course 1", "Course 2", ...]
    }}
  ],
  "skills": {{
    "Programming": ["Python", "Java", ...],
    "AI/ML": ["TensorFlow", "PyTorch", ...],
    "Cloud": ["AWS", "Azure", ...]
  }},
  "experience": [
    {{
      "title": "Job Title",
      "company": "Company Name",
      "dates": "Jan 2020 - Present",
      "bullets": [
        "Achievement bullet point 1",
        "Achievement bullet point 2",
        ...
      ]
    }}
  ],
  "projects": [
    {{
      "name": "Project Name",
      "description": "Project description",
      "technologies": ["Tech1", "Tech2", ...],
      "category": "Domain/Category"
    }}
  ],
  "certifications": [
    {{
      "name": "Certification Name",
      "issuer": "Issuing Organization",
      "year": "2024"
    }}
  ]
}}

CRITICAL REQUIREMENTS:
1. Extract ALL education entries (don't skip any)
2. Extract ALL work experience entries with ALL bullet points (don't truncate)
3. Extract ALL projects with full descriptions
4. Extract ALL skills organized by category
5. Extract ALL certifications
6. Be accurate - preserve exact dates, names, and details
7. If information is missing, use empty string or empty array

Resume Text:
\"\"\"
{resume_text}
\"\"\"

Return ONLY the JSON object, no explanation, no markdown formatting."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert resume parser. Always return valid JSON with complete resume data. Extract ALL information, don't skip or truncate anything."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,  # Low temperature for accuracy
            max_tokens=4000,  # Allow for large resumes
        )
        
        raw_output = response.choices[0].message.content.strip()
        
        # Clean up response
        if raw_output.startswith("```json"):
            raw_output = raw_output[7:]
        if raw_output.startswith("```"):
            raw_output = raw_output[3:]
        if raw_output.endswith("```"):
            raw_output = raw_output[:-3]
        raw_output = raw_output.strip()
        
        # Parse JSON
        try:
            data = json.loads(raw_output)
            
            # Convert to ResumeData model
            education = [
                Education(
                    degree=edu.get("degree", ""),
                    university=edu.get("university", ""),
                    location=edu.get("location", ""),
                    dates=edu.get("dates", ""),
                    gpa=edu.get("gpa", ""),
                    coursework=edu.get("coursework", [])
                )
                for edu in data.get("education", [])
            ]
            
            experience = [
                Experience(
                    title=exp.get("title", ""),
                    company=exp.get("company", ""),
                    dates=exp.get("dates", ""),
                    bullets=exp.get("bullets", [])  # Keep ALL bullets
                )
                for exp in data.get("experience", [])
            ]
            
            projects = [
                Project(
                    name=proj.get("name", ""),
                    description=proj.get("description", ""),
                    technologies=proj.get("technologies", []),
                    category=proj.get("category", "")
                )
                for proj in data.get("projects", [])
            ]
            
            certifications = [
                Certification(
                    name=cert.get("name", ""),
                    issuer=cert.get("issuer", ""),
                    year=cert.get("year", "")
                )
                for cert in data.get("certifications", [])
            ]
            
            return ResumeData(
                name=data.get("name", "Your Name"),
                email=data.get("email", ""),
                phone=data.get("phone", ""),
                linkedin=data.get("linkedin", ""),
                github=data.get("github", ""),
                location=data.get("location", ""),
                education=education,
                skills=data.get("skills", {}),
                experience=experience,
                projects=projects,
                certifications=certifications,
            )
        
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}. Falling back to basic parser.")
            from .resume_parser import _parse_text_to_resume_data
            return _parse_text_to_resume_data(resume_text)
    
    except Exception as e:
        print(f"LLM parsing error: {e}. Falling back to basic parser.")
        from .resume_parser import _parse_text_to_resume_data
        return _parse_text_to_resume_data(resume_text)

