import os
import sys
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Validate API key on startup
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("❌ ERROR: OPENAI_API_KEY environment variable is not set.")
    print("Please set it using: export OPENAI_API_KEY='your-key-here'")
    print("Or create a .env file with: OPENAI_API_KEY=your-key-here")
    sys.exit(1)

client = OpenAI(api_key=api_key)
app = Flask(__name__)

# Define limits that match the frontend (enforce server-side to prevent abuse)
TEXT_MAX_LENGTH = 5000
QUESTION_MAX_LENGTH = 300
TEXT_MIN_LENGTH = 20
QUESTION_MIN_LENGTH = 3

SYSTEM_PROMPT = """You are an AI assistant designed to help students and staff at Metropolia UAS.
Your role is to help with course materials, lecture notes, and educational questions.
Provide clear, concise, and helpful answers. If the question is outside the scope of the provided text, say so.
Keep responses focused and structured."""

def ask_model(prompt, max_tokens=300):
    """Query OpenAI API with the given prompt.

    This function wraps the OpenAI client call and normalizes the response.
    Keep the function small so it's easy to mock in tests or swap providers.
    """
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.2
        )

        # Newer OpenAI client returns message objects where content is an attribute
        # rather than a dict. Normalize to string and strip whitespace.
        return resp.choices[0].message.content.strip()
    except Exception as e:
        # Raise a generic error that will be converted to a friendly message
        # by the endpoint. In a larger app we'd log more context and use
        # structured logging.
        raise Exception(f"API Error: {str(e)}")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
def ask():
    """Process user questions against lecture text.

    Expected JSON body: { "text": "<lecture text>", "question": "<user question>" }
    Returns JSON: { "answer": "..." } on success, or { "error": "..." } on failure.
    """
    try:
        data = request.json
        # Handle None/null values by converting to empty strings
        text = (data.get("text") or "").strip()
        question = (data.get("question") or "").strip()

        # Input validation
        if not text:
            return jsonify({"error": "Please provide lecture text."}), 400
        if not question:
            return jsonify({"error": "Please enter a question."}), 400
        if len(text) < TEXT_MIN_LENGTH:
            return jsonify({"error": "Lecture text is too short. Please provide more content."}), 400
        if len(question) < QUESTION_MIN_LENGTH:
            return jsonify({"error": "Question is too short. Please be more specific."}), 400
        if len(text) > TEXT_MAX_LENGTH:
            return jsonify({"error": f"Lecture text exceeds maximum length ({TEXT_MAX_LENGTH} characters). Please shorten it."}), 400
        if len(question) > QUESTION_MAX_LENGTH:
            return jsonify({"error": f"Question exceeds maximum length ({QUESTION_MAX_LENGTH} characters). Please shorten it."}), 400

        prompt = f"Based on the following course material, please answer the question.\n\nCourse Material:\n{text}\n\nQuestion: {question}\n\nProvide a clear and concise answer."

        answer = ask_model(prompt)
        return jsonify({"answer": answer})

    except Exception as e:
        # Log the exception server-side for debugging, but return a generic
        # message to the client to avoid leaking internals.
        print(f"Error in /ask endpoint: {str(e)}")
        return jsonify({"error": "An error occurred. Please try again later."}), 500

@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    print("🚀 Metropolia Course FAQ Assistant is starting...")
    print("📖 Open http://localhost:5000 in your browser")
    app.run(debug=True, port=5000)
