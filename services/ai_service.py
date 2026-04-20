import os
import json
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

class GroqOpenAIService:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        
        # Initialize the async client only if environment variables are present
        if self.api_key:
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url="https://api.groq.com/openai/v1"
            )
        else:
            self.client = None

    async def generate_tailored_application(self, resume_text: str, job_description: str) -> dict:
        """
        Generates a tailored cover letter and missing skills analysis.
        """
        if not self.client:
             raise ValueError("Groq client is not properly initialized. Check your GROQ_API_KEY environment variable.")

        system_prompt = """You are an expert ATS (Applicant Tracking System) analyzer. Your goal is to compare a Resume against a Job Description.
Analyze the user's original resume bullets. Identify 2 to 3 existing bullets that can be rewritten to naturally incorporate some of the identified `missing_keywords`.
Based on the Job Description and the candidate's `missing_keywords`, generate 3 highly targeted technical interview questions the candidate is likely to be asked to test their knowledge gaps.
You must output a structured JSON response containing EXACTLY the following format:
{
  "job_title": "A concise title extracted from the job description (e.g. 'Senior Frontend Developer')",
  "match_score": (A number between 0-100 representing the fit),
  "analysis_summary": "A 2-sentence explanation of why the score was given.",
  "missing_keywords": ["Skill 1", "Skill 2", "Skill 3"],
  "matched_skills": ["Skill A", "Skill B"],
  "suggested_rewrites": [
    {
      "original_bullet": "The exact bullet from the user's resume.",
      "upgraded_bullet": "The rewritten bullet including the new keyword naturally.",
      "keyword_added": "The specific missing keyword targeted."
    }
  ],
  "interview_prep": [
    {
      "question": "The specific technical interview question.",
      "why_its_asked": "A brief explanation of why the interviewer cares about this concept.",
      "how_to_answer": "A short, actionable tip or framework on how the candidate should respond."
    }
  ],
  "cover_letter": "A highly tailored, professional cover letter (max 300 words). It MUST NOT invent any skills or degrees not found in the resume."
}

Output strictly valid JSON."""

        user_prompt = f"RESUME:\n{resume_text}\n\nJOB DESCRIPTION:\n{job_description}"

        response = await self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={ "type": "json_object" },
            temperature=0.7
        )
        
        result_text = response.choices[0].message.content
        
        try:
            return json.loads(result_text)
        except json.JSONDecodeError:
            raise ValueError("Failed to parse JSON response from Groq OpenAI wrapper.")

    async def enhance_job_description(self, draft_text: str) -> str:
        response = await self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a professional technical recruiter. Take the user's messy job description draft and expand it into a clean, professional, Big Tech-style job description. Use bullet points for responsibilities and requirements. Return ONLY the polished text with no conversational filler."},
                {"role": "user", "content": f"Enhance this job description: {draft_text}"}
            ]
        )
        return response.choices[0].message.content.strip()

# Singleton instance for dependency injection
ai_service = GroqOpenAIService()
