from flask import Flask, request, render_template_string
import asyncio
from playwright.sync_api import sync_playwright
import pandas as pd
from datetime import datetime

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Instagram Competitor Analyzer</title>
</head>
<body>
    <h1>📊 Instagram Competitor Analyzer</h1>
    <form method="POST">
        <label>Enter Instagram Username:</label><br>
        <input type="text" name="username" required><br><br>

        <label>Filter by date (YYYY-MM-DD):</label><br>
        <input type="text" name="filter_date"><br><br>

        <input type="submit" value="Analyze">
    </form>

    {% if data %}
        <h2>Analysis Results for {{ username }}</h2>
        <p><strong>Total Posts:</strong> {{ total_posts }}</p>

        {% if filtered_data %}
            <h3>Posts on {{ filter_date }}:</h3>
            <ul>
                {% for post in filtered_data %}
                    <li>{{ post['date'] }} - {{ post['caption'][:50] }}...</li>
                {% endfor %}
            </ul>
        {% endif %}

        <h3>Suggested Growth Strategy ({{ niche }} niche):</h3>
        <ul>
            <li>Post at peak times (9 AM to 11 AM, 6 PM to 8 PM)</li>
            <li>Use trending audio in reels</li>
            <li>Engage with similar accounts' audiences</li>
            <li>Use 5-10 high-quality hashtags related to {{ niche }}</li>
        </ul>
    {% endif %}
</body>
</html>
"""

def scrape_instagram(username):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        url = f'https://www.instagram.com/{username}/'
        page.goto(url)
        page.wait_for_timeout(3000)

        content = page.content()
        if '"edge_owner_to_timeline_media"' not in content:
            browser.close()
            return None

        json_data = page.locator('script[type="application/ld+json"]').nth(0).inner_text()
        page_data = page.locator('script').nth(4).inner_text()
        start = page_data.find('{"config":')
        end = page_data.find('};') + 1
        raw_json = page_data[start:end]

        import json
        data_json = json.loads(raw_json)
        posts_data = data_json["entry_data"]["ProfilePage"][0]["graphql"]["user"]["edge_owner_to_timeline_media"]["edges"]

        posts = []
        for post in posts_data:
            node = post["node"]
            timestamp = datetime.fromtimestamp(node["taken_at_timestamp"])
            caption = node["edge_media_to_caption"]["edges"][0]["node"]["text"] if node["edge_media_to_caption"]["edges"] else ""
            posts.append({
                "date": timestamp.strftime("%Y-%m-%d %H:%M"),
                "caption": caption
            })

        browser.close()
        return posts

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        username = request.form['username']
        filter_date = request.form.get('filter_date')

        posts = scrape_instagram(username)
        if not posts:
            return "Could not fetch Instagram data. Make sure profile is public."

        total_posts = len(posts)
        filtered_data = [p for p in posts if filter_date in p['date']] if filter_date else []

        # Simple niche suggestion (you could make this dynamic)
        niche = "comedy" if "funny" in username or "comedy" in username else "general"

        return render_template_string(HTML_TEMPLATE,
                                      username=username,
                                      data=True,
                                      total_posts=total_posts,
                                      filtered_data=filtered_data,
                                      filter_date=filter_date,
                                      niche=niche)

    return render_template_string(HTML_TEMPLATE)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=10000)
