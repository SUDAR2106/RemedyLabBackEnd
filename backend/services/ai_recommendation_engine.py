# services/ai_recommendation_engine.py
import os
import json
from openai import OpenAI
from dotenv import load_dotenv

# from config import OPENAI_API_KEY

# Load API key from .env
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# Ensure API key is available
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set.")

client = OpenAI(api_key=api_key)

def build_ai_prompt(extracted_data: dict) -> str:
    """
    Constructs a detailed prompt for the AI based on extracted health data.
    """
    lines = [
        "You are an expert AI assistant specialized in functional and integrative medicine.",
        "Analyze the following health report data and provide concise, actionable recommendations.",
        "Your output MUST be a JSON object with the following keys:",
        "- 'treatment_suggestions': A string containing medical treatment suggestions (if needed).",
        "- 'lifestyle_recommendations': A string containing personalized lifestyle and diet recommendations, and stress/wellness strategies.",
        "- 'priority': A string indicating the urgency (e.g., 'High', 'Medium', 'Low').",
        "",
        "Health Report Data (JSON format):"
    ]
    lines.append(json.dumps(extracted_data, indent=2))
    lines.append("\nEnsure the JSON is perfectly formed and contains only the specified keys.")
    
    return "\n".join(lines)

def generate_ai_recommendations(extracted_data: dict) -> dict:
    """
    Sends extracted health data to an OpenAI LLM to get structured recommendations.
    Returns a dictionary with 'treatment_suggestions', 'lifestyle_recommendations', 'priority'.
    Returns None if generation or parsing fails.
    """
    if not extracted_data:
        print("AI Recommendation Engine: No extracted data provided.")
        return None

    prompt = build_ai_prompt(extracted_data)
    print("AI Recommendation Engine: Sending prompt to OpenAI...")

    try:
        # Use gemini-2.0-flash for consistency with previous instructions if needed,
        # but the user provided openai code, so sticking to that.
        # If you need to switch to Gemini, the fetch API call would be different.
        response = client.chat.completions.create(
            model="gpt-4o-mini", # Using the model specified by the user
            messages=[
                {"role": "system", "content": "You are a trusted AI health assistant that outputs valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1500,
            response_format={"type": "json_object"} # Crucial for structured output
        )

        ai_response_content = response.choices[0].message.content
        print("AI Recommendation Engine: Raw AI response received.")
        
        # Attempt to parse the JSON response
        parsed_response = json.loads(ai_response_content)
        print(f"AI Recommendation Engine: Parsed AI response: {parsed_response}")
        # Validate expected keys
        required_keys = ['treatment_suggestions', 'lifestyle_recommendations', 'priority']
        if all(key in parsed_response for key in required_keys):
            print("AI Recommendation Engine: Successfully parsed AI recommendations.")
            return {
                'treatment_suggestions': parsed_response.get('treatment_suggestions', ''),
                'lifestyle_recommendations': parsed_response.get('lifestyle_recommendations', ''),
                'priority': parsed_response.get('priority', 'Medium') # Default to Medium if not provided
            }
        else:
            print(f"AI Recommendation Engine: Missing required keys in AI response: {parsed_response.keys()}")
            return None

    except json.JSONDecodeError as e:
        print(f"AI Recommendation Engine: Failed to parse AI response as JSON: {e}")
        print(f"Raw AI content: {ai_response_content[:500]}...")
        return None
    except Exception as e:
        print(f"AI Recommendation Engine: Error calling OpenAI API: {e}")
        return None

# # Example usage for testing (can be run directly for debugging)
# if __name__ == "__main__":
#     # Dummy extracted data for testing
#     dummy_extracted_data = {
#         "blood_glucose": {"value": 120, "unit": "mg/dL", "normal_range": "70-100"},
#         "cholesterol_total": {"value": 220, "unit": "mg/dL", "normal_range": "<200"},
#         "hba1c": {"value": 6.8, "unit": "%", "normal_range": "<5.7"},
#         "blood_pressure": "140/90 mmHg",
#         "symptoms": ["fatigue", "frequent urination"]
#     }
    
#     print("\n--- Testing AI Recommendation Engine ---")
#     recommendations = generate_ai_recommendations(dummy_extracted_data)
    
#     if recommendations:
#         print("\n✅ Generated Recommendations:")
#         print(f"Treatment: {recommendations['treatment_suggestions']}")
#         print(f"Lifestyle: {recommendations['lifestyle_recommendations']}")
#         print(f"Priority: {recommendations['priority']}")
#     else:
#         print("\n❌ Failed to generate recommendations.")