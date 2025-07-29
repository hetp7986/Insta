from flask import Flask, render_template, request, send_file
import instaloader
import pandas as pd
from datetime import datetime
import os

app = Flask(__name__)
L = instaloader.Instaloader()

def analyze_profile(username, num_posts):
    try:
        profile = instaloader.Profile.from_username(L.context, username)
    except Exception as e:
        return None, str(e)

    posts_data = []
    for idx, post in enumerate(profile.get_posts(), 1):
        if idx > num_posts:
            break
        post_data = {
            'Post': f'Post {idx}',
            'Date': post.date_utc.strftime('%Y-%m-%d'),
            'Time': post.date_utc.strftime('%H:%M:%S'),
            'Likes': post.likes,
            'Comments': post.comments,
            'Views': post.video_view_count if post.is_video else 'N/A',
            'Caption': post.caption[:50] if post.caption else '',
        }
        posts_data.append(post_data)

    df = pd.DataFrame(posts_data)
    df['Day'] = pd.to_datetime(df['Date']).dt.day_name()

    best_day = df['Day'].mode()[0]
    best_hour = pd.to_datetime(df['Time']).dt.hour.mode()[0]

    analysis = {
        'most_common_day': best_day,
        'most_common_hour': best_hour,
    }

    file_path = f"{username}_report.csv"
    df.to_csv(file_path, index=False)
    return analysis, file_path

@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    error = None
    file_url = None
    if request.method == 'POST':
        username = request.form['username'].strip().lstrip('@')
        posts_limit = int(request.form['num_posts'])
        analysis, file_path = analyze_profile(username, posts_limit)
        if analysis:
            result = analysis
            file_url = f"/download/{file_path}"
        else:
            error = file_path
    return render_template('index.html', result=result, error=error, file_url=file_url)

@app.route('/download/<filename>')
def download(filename):
    return send_file(filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
