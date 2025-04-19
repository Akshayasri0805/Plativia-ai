from flask import Flask, render_template, request, session, url_for
import google.generativeai as genai
import re
import os
import uuid

app = Flask(__name__)
app.secret_key = "supersecretkey123"

# Initialize Gemini
genai.configure(api_key="AIzaSyBHUaROcHN_uKc7pkDIb57qna3O79wWOWg")  # Replace with your actual key

def format_recipe_text(text):
    macro_data = {}

    text = re.sub(r'Recipe Name:\s*(.*)', r'<h2>🍽️ Recipe Name: \1</h2>', text)
    text = re.sub(r'(?i)Ingredients:', r'<h3>🧂 Ingredients</h3><ul>', text)
    text = re.sub(r'(?i)Instructions:', r'</ul><h3>👨‍🍳 Instructions</h3><ol>', text)
    text = re.sub(r'\n\*\*(.*?)\*\*', r'<li><strong>\1</strong></li>', text)
    text = re.sub(r'\n\s*\d+\.\s*(.+)', r'<li>\1</li>', text)
    text = re.sub(r'\n\*\s*(.+)', r'<li>\1</li>', text)
    text = re.sub(r'Estimated Budget:\s*(.*?)\n', r'<h3>💰 Estimated Budget</h3><p>\1</p>\n', text)
    text = re.sub(r'Servings Per Batch:\s*(.*?)\n', r'<h3>🔁 Servings Per Batch</h3><p>\1</p>\n', text)
    text += "</ol>"

    # Extract macro values
    macro_match = re.search(
        r'Calories:\s*(\d+).*?Protein:\s*(\d+).*?Carbs:\s*(\d+).*?Fat:\s*(\d+)',
        text, re.DOTALL
    )
    if macro_match:
        calories, protein, carbs, fat = macro_match.groups()
        macro_data = {
            "calories": int(calories),
            "protein": int(protein),
            "carbs": int(carbs),
            "fat": int(fat)
        }

    # Insert macro HTML
    text = re.sub(
        r'Macronutrients:\s*\(?.*?\)?\s*Calories:\s*\d+\s*Protein:\s*\d+\s*Carbs:\s*\d+\s*Fat:\s*\d+',
        f'<h3>⚖️ Macronutrients (Per Serving)</h3><ul>'
        f'<li><strong>Calories:</strong> {macro_data.get("calories", "-")}</li>'
        f'<li><strong>Protein:</strong> {macro_data.get("protein", "-")} g</li>'
        f'<li><strong>Carbohydrates:</strong> {macro_data.get("carbs", "-")} g</li>'
        f'<li><strong>Fat:</strong> {macro_data.get("fat", "-")} g</li>'
        f'</ul>',
        text, flags=re.DOTALL
    )

    return text, macro_data

def linkify_ingredients(html_recipe):
    try:
        ingredients_start = html_recipe.index('<ul>')
        instructions_start = html_recipe.index('</ul>')

        ingredients_list = html_recipe[ingredients_start:instructions_start]
        linked_ingredients = '<p><strong>🛒 Come let\'s go for a quick shopping!</strong></p>'

        def make_link(match):
            line = match.group(1)
            words = re.sub(r'[^\w\s]', '', line).split()
            if words:
                keywords = [w for w in words if w.lower() not in ['cup', 'cups', 'tbsp', 'tablespoon', 'tsp', 'teaspoon', 'of', 'a', 'an']]

                item = keywords[-1] if keywords else words[-1]
                url = f"https://www.blinkit.com/s/?q={item.replace(' ', '+')}"
                return f'<li><a href="{url}" target="_blank">{line}</a></li>'
            return f'<li>{line}</li>'

        linked_ingredients += re.sub(r'<li>(.*?)</li>', make_link, ingredients_list)
        return html_recipe[:ingredients_start] + linked_ingredients + html_recipe[instructions_start:]
    except Exception as e:
        print("Linkify error:", e)
        return html_recipe

@app.route("/", methods=["GET", "POST"])
def index():
    macro_data = {}

    session["chat_history"] = []

    if request.method == "POST":
        prompt = request.form["prompt"]
        cuisine = request.form.get("cuisine", "")
        time = request.form.get("time", "")

        final_prompt = f"""Create a detailed recipe with the following requirements:
- Cuisine: {cuisine if cuisine else 'any'}
- Cooking Time: {time if time else 'flexible'} minutes
- Recipe for: {prompt}

Please format the response in clear sections:

Recipe Name:
Ingredients:
[List all ingredients with measurements]

Instructions:
[Step by step cooking instructions]

Macronutrients:
[Total approximate values per serving — Calories, Protein (g), Carbs (g), Fat (g)]

Estimated Budget:
[Approximate cost in INR or USD]

Servings Per Batch:
[How many servings can be made from one standard grocery purchase of ingredients]

Make sure sections are clearly marked as above.
"""

        model = genai.GenerativeModel('models/gemini-1.5-pro')
        response = model.generate_content(final_prompt)
        raw_recipe = response.text.strip()

        formatted, macro_data = format_recipe_text(raw_recipe)
        linked = linkify_ingredients(formatted)

        # Use a static image for the chart (mocking the real data)
        static_chart_path = os.path.join("static", "charts", "mock_chart.png")
        macro_data["chart_path"] = static_chart_path

        session["chat_history"].append({
            "user": prompt,
            "bot": linked,
            "macros": macro_data
        })

        session.modified = True

    return render_template("index.html", chat_history=session["chat_history"], macro_data=macro_data)

if __name__ == "__main__":
    app.run(debug=True)
