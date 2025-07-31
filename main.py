from flask import Flask, request, render_template_string
from playwright.sync_api import sync_playwright
import pandas as pd
import datetime
import re

app = Flask(__name__)

TEMPLATE = """
<!doctype html>
<html>
<head>
    <title>Instagram Competitor Analyzer</title>
    <style>
        body { font-family: Arial; margin: 2em; background-color: #f0f0f0; }
        input, button { padding: 8px; margin: 5px; }
        .card { background: #fff; padding: 1em; margin-bottom: 1em; border-radius: 8px; box-shadow: 0 2px 5px #ccc; }
        h2 { margin-top: 2em; }
    </style>
</head>
<body>
    <h1>Instagram Competitor Analyzer</h1>
    <form method="POST">
        <label>Instagram Username:</label><br>
        <input name="username" placeholder="e.g. kingbach" required><br>
        <label>Filter by Date (optional):</label><br>
        <input name="date" type="date"><br>
        <button type="submit">Analyze</button>
    </form>

    {% if posts %}
        <h2>Results for @{{ username }}</h2>
        <p><strong>Total Posts Fetched:</strong> {{ posts|length }}</p>

        {% if date %}
            <h3>📅 Posts on {{ date }}</h3>
            {% for post in posts %}
                {% if post.timestamp.date() == date_obj %}
                    <div class="card">
                        <a href="{{ post.url }}" target="_blank">{{ post.url }}</a><br>
                        Time: {{ post.timestamp.time() }}<br>
                        Caption: {{ post.caption[:100] }}...
                    </div>
                {% endif %}
            {% endfor %}
        {% else %}
            <h3>📄 All Posts</h3>
            {% for post in posts %}
                <div class="card">
                    <a href="{{ post.url }}" target="_blank">{{ post.url }}</a><br>
                    Time: {{ post.timestamp }}<br>
                    Caption: {{ post.caption[:100] }}...
                </div>
            {% endfor %}
        {% endif %}

        <h3>📈 Growth Suggestions</h3>
        <ul>
            {% for suggestion in suggestions %}
                <li>{{ suggestion }}</li>
            {% endfor %}
        </ul>
    {% endif %}
</body>
</html>
"""

def scrape_instagram(username):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"https://www.instagram.com/{username}/")
        page.wait_for_selector("article")

        post_links = page.eval_on_selector_all(
            "article a", "elements => elements.map(e => e.href)"
        )[:30]

        posts = []
        for link in post_links:
            page.goto(link)
            page.wait_for_timeout(2000)

            try:
                caption = page.locator("xpath=//div[@data-testid='post-comment-root']").first.inner_text()
            except:
                caption = "N/A"

            try:
                time_text = page.locator("time").get_attribute("datetime")
                timestamp = datetime.datetime.fromisoformat(time_text.replace("Z", "+00:00"))
            except:
                timestamp = "N/A"

            posts.append({
                "url": link,
                "caption": caption,
                "timestamp": timestamp
            })

        browser.close()
        return posts

def generate_suggestions(posts):
    suggestions = []
    if len(posts) < 10:
        suggestions.append("Post more frequently (4–5 times/week recommended).")

    hashtags = [tag for p in posts for tag in re.findall(r"#\w+", p["caption"])]
    top_tags = pd.Series(hashtags).value_counts().head(5)

    if not top_tags.empty:
        suggestions.append("Top hashtags used: " + ", ".join(top_tags.index.tolist()))
    else:
        suggestions.append("Use more niche-specific hashtags to increase visibility.")

    if any(tag in top_tags.index for tag in ["#funny", "#comedy"]):
        suggestions.append("Niche detected: Comedy — Use reels with trending audio and short skits.")
    elif any(tag in top_tags.index for tag in ["#fashion", "#style"]):
        suggestions.append("Niche detected: Fashion — Post OOTD, style tips, and tag relevant brands.")
    else:
        suggestions.append("No strong niche detected. Try using more focused hashtags.")
    
    return suggestions

@app.route("/", methods=["GET", "POST"])
def index():
    posts = []
    suggestions = []
    username = ''
    date = request.form.get("date")
    date_obj = None

    if request.method == "POST":
        username = request.form["username"].strip().lower()
        posts = scrape_instagram(username)
        suggestions = generate_suggestions(posts)
        if date:
            try:
                date_obj = datetime.datetime.strptime(date, "%Y-%m-%d").date()
            except:
                date_obj = None

    return render_template_string(TEMPLATE, posts=posts, username=username, suggestions=suggestions, date=date, date_obj=date_obj)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
