from openai import OpenAI
import os

# ==================================================
# CONFIG AI BRAIN
# ==================================================

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ==================================================
# AI BRAIN ADVICE
# ==================================================
def generate_advice(prompt: str):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content
