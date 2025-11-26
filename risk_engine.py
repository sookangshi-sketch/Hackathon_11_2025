import pandas as pd
import joblib
import os
import google.generativeai as genai

# 1. Load your teammate's "Math Brain"
try:
    rf_model = joblib.load("baseline_model_rf.pkl")
    print("✅ Teammate's model loaded!")
except Exception as e:
    print(f"❌ Model not found: {e}")
    print("Please run train_model.py first to generate the model.")
    rf_model = None

# Initialize Gemini client with API key
# Initialize Gemini client with API key
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash')
    print("✅ Gemini client initialized with API key")
else:
    model = None
    print("⚠️ No API key found. Text analysis will use fallback scoring.")

def get_total_risk(age, income, loan_amount, loan_term, dti, credit_history, dependents, user_story):
    
    # --- PART 1: THE MATH BRAIN (Teammate's Code) ---
    math_risk_score = 0
    if rf_model is None:
        raise ValueError("Model not loaded. Please run train_model.py first to generate baseline_model_rf.pkl")
    
    try:
        # We must format the data exactly how your teammate trained it
        # Features: ["age", "monthly_income", "loan_amount", "loan_term", "dti", "credit_history", "num_dependents"]
        input_data = pd.DataFrame([[age, income, loan_amount, loan_term, dti, credit_history, dependents]], 
                                  columns=["age", "monthly_income", "loan_amount", "loan_term", "dti", "credit_history", "num_dependents"])
        
        # Get probability of default (0 to 1)
        # We multiply by 100 to make it a percentage
        math_risk_score = rf_model.predict_proba(input_data)[0][1] * 100
    except Exception as e:
        raise ValueError(f"Error calculating math risk score: {e}")

    # --- PART 2: THE TEXT BRAIN (Enhanced LLM Analysis) ---
    text_risk_score = 50  # Default fallback score
    text_analysis = {}  # Store detailed analysis
    use_fallback = False  # Flag to trigger enhanced fallback
    
    if model is not None:
        prompt = f"""You are a credit risk analyst evaluating loan applications based on the applicant's stated purpose.

Analyze the following loan application story across multiple risk dimensions:

Applicant Story: "{user_story}"

Evaluate these factors (each scored 0-100, where 0 is lowest risk and 100 is highest risk):

1. **Purpose Legitimacy** (0-100): Is the stated purpose credible, specific, and legitimate? Vague or suspicious purposes score higher.

2. **Financial Responsibility** (0-100): Does the story indicate responsible financial planning and behavior? Signs of poor planning or impulsiveness score higher.

3. **Urgency/Desperation** (0-100): Are there signs of financial distress, desperation, or time pressure? Higher urgency indicates higher risk.

4. **Clarity** (0-100): Is the explanation clear, detailed, and coherent? Vague or unclear stories score higher.

5. **Red Flags** (0-100): Presence of high-risk indicators like gambling, debt consolidation, legal issues, or evasiveness.

Provide your analysis in JSON format with this exact structure:
{{
  "purpose_legitimacy": <score 0-100>,
  "financial_responsibility": <score 0-100>,
  "urgency_desperation": <score 0-100>,
  "clarity": <score 0-100>,
  "red_flags": <score 0-100>,
  "overall_risk": <weighted average score 0-100>,
  "confidence": <your confidence in this assessment 0-100>,
  "explanation": "<brief 1-2 sentence explanation of the overall risk>"
}}"""
        
        try:
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.3,  # Lower temperature for more consistent scoring
                    response_mime_type="application/json"
                )
            )
            
            import json
            text_analysis = json.loads(response.text)
            text_risk_score = int(text_analysis.get('overall_risk', 50))
            
            print(f"✅ Gemini Analysis: Risk={text_risk_score}, Confidence={text_analysis.get('confidence', 'N/A')}")
            print(f"   Explanation: {text_analysis.get('explanation', 'N/A')}")
            
        except Exception as e:
            print(f"⚠️ Gemini API error: {e}. Using enhanced fallback.")
            # Trigger enhanced fallback instead of using simple default
            use_fallback = True
    else:
        use_fallback = True
    
    if use_fallback:
        # Enhanced Fallback: Sophisticated heuristic analysis
        print("⚠️ Using enhanced fallback text analysis (no OpenAI API key)")
        
        # Expanded keyword lists
        high_risk_keywords = [
            'gambling', 'casino', 'lottery', 'bet', 'poker',
            'debt', 'owe', 'collection', 'bankruptcy', 'foreclosure',
            'desperate', 'urgent', 'emergency', 'asap', 'immediately',
            'legal trouble', 'lawsuit', 'court', 'fine', 'penalty',
            'loan shark', 'payday', 'cash advance'
        ]
        
        medium_risk_keywords = [
            'bills', 'overdue', 'late payment', 'catch up',
            'unexpected', 'surprise', 'didn\'t plan',
            'personal reasons', 'rather not say', 'private'
        ]
        
        low_risk_keywords = [
            'business', 'expansion', 'investment', 'equipment',
            'education', 'training', 'certification', 'degree',
            'home improvement', 'renovation', 'repair',
            'medical', 'healthcare', 'treatment',
            'consolidation', 'refinance', 'lower interest',
            'startup', 'entrepreneur', 'venture', 'project'
        ]
        
        story_lower = user_story.lower()
        
        # Count keyword matches
        high_risk_count = sum(1 for word in high_risk_keywords if word in story_lower)
        medium_risk_count = sum(1 for word in medium_risk_keywords if word in story_lower)
        low_risk_count = sum(1 for word in low_risk_keywords if word in story_lower)
        
        # Story length and clarity analysis
        word_count = len(user_story.split())
        clarity_penalty = 0
        if word_count < 5:
            clarity_penalty = 20  # Very vague
        elif word_count < 10:
            clarity_penalty = 10  # Somewhat vague
        
        # Calculate risk score with weighted factors
        base_score = 50
        risk_adjustment = (high_risk_count * 15) + (medium_risk_count * 8) - (low_risk_count * 12)
        
        text_risk_score = max(0, min(100, base_score + risk_adjustment + clarity_penalty))
        
        text_analysis = {
            "fallback": True,
            "high_risk_matches": high_risk_count,
            "medium_risk_matches": medium_risk_count,
            "low_risk_matches": low_risk_count,
            "word_count": word_count,
            "clarity_penalty": clarity_penalty
        }

    # --- PART 3: FUSION (The Hackathon Requirement) ---
    # We weigh the Math model 70% and the Text model 30%
    final_score = (math_risk_score * 0.7) + (text_risk_score * 0.3)
    
    return {
        "Math_Score": round(math_risk_score, 1),
        "Text_Score": text_risk_score,
        "Final_Risk": round(final_score, 1),
        "Text_Analysis": text_analysis  # Include detailed LLM analysis
    }