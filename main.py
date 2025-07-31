from flask import Flask, request, render_template_string
from playwright.sync_api import sync_playwright
import pandas as pd
import os

app = Flask(__name__)

# HTML UI (embedded in Python)
html = """
<!DOCTYPE html>
<html>
<head>
    <title>Instagram Competitor Analysis</title>
</head>
<body>
    <h2>Instagram Competitor Analyzer</h2>
    <form method="post" action="/analyze">
        <label>Instagram Username:</label>
        <input type="text" name="username" required><br><br>
        <label>Date (optional, YYYY-MM-DD):</label>
        <input type="text" name="date"><br><br>
        <button type="submit">Analyze</button>
    </form>
    {% if result %}
        <h3>Account: {{ result.username }}</h3>
        <p>Total Posts: {{ result.total_posts }}</p>
        <h4>Post Details:</h4>
        <ul>
        {% for post in result.posts %}
            <li>{{ post }}</li>
        {% endfor %}
        </ul>
        <h4>Suggestions:</h4>
        <p>{{ result.suggestions }}</p>
    {% endif %}
</body>
</html>
"""

# Function to scrape data using Playwright
def scrape_instagram(username, date_filter=None):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        url = f"https://www.instagram.com/{username}/"
        page.goto(url, timeout=60000)
        page.wait_for_selector("article", timeout=15000)

        # Extract post timestamps from script tags
        content = page.content()
        scripts = page.query_selector_all("script")
        posts_data = []
        for script in scripts:
            content = script.inner_text()
            if "edge_owner_to_timeline_media" in content:
                try:
                    json_data = content.split("window._sharedData = ")[1].split(";</script>")[0]
                    import json
                    data = json.loads(json_data)
                    edges = data['entry_data']['ProfilePage'][0]['graphql']['user']['edge_owner_to_timeline_media']['edges']
                    for edge in edges:
                        timestamp = pd.to_datetime(edge['node']['taken_at_timestamp'], unit='s')
                        if not date_filter or str(timestamp.date()) == date_filter:
                            posts_data.append(str(timestamp))
                    break
                except Exception:
                    continue

        browser.close()

        suggestions = "Post consistently and use relevant hashtags. Observe top-performing times from your competitor."
        return {
            "username": username,
            "total_posts": len(posts_data),
            "posts": posts_data,
            "suggestions": suggestions
        }

@app.route('/', methods=['GET'])
def home():
    return render_template_string(html)

@app.route('/analyze', methods=['POST'])
def analyze():
    username = request.form['username']
    date_filter = request.form.get('date')
    result = scrape_instagram(username, date_filter)
    return render_template_string(html, result=result)

if __name__ == "__main__":
    # Download Playwright browser on first run
    if not os.path.exists(os.path.expanduser("~/.cache/ms-playwright")):
        os.system("playwright install chromium")
    app.run(host="0.0.0.0", port=5000)
