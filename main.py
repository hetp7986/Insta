from flask import Flask, request, jsonify, send_file
import pandas as pd
import os
import datetime
import instaloader
import re
from collections import Counter
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px

app = Flask(__name__)

# Global variable to store scraped data
scraped_data = None

# --- Scraper Functions (from scraper.py) ---
def scrape_instagram_profile(username):
    L = instaloader.Instaloader()
    # You might need to login if the profile is private or to avoid rate limits
    # L.load_session_from_file(YOUR_USERNAME, YOUR_SESSION_FILE_PATH)

    try:
        profile = instaloader.Profile.from_username(L.context, username)
    except Exception as e:
        print(f"Error: Could not load profile {username}. {e}")
        return pd.DataFrame()

    posts_data = []
    for post in profile.get_posts():
        posts_data.append({
            'post_id': post.mediaid,
            'caption': post.caption,
            'likes': post.likes,
            'comments': post.comments,
            'views': post.video_view_count if post.is_video else None,
            'post_type': 'video' if post.is_video else 'image',
            'timestamp': post.date_utc
        })
    df = pd.DataFrame(posts_data)
    return df

# --- Analyzer Functions (from analyzer.py, modified for offline NLP) ---
def analyze_sentiment(text):
    if not isinstance(text, str):
        return 'neutral'
    text = text.lower()
    positive_words = ["love", "great", "happy", "amazing", "good", "best", "beautiful", "fun", "awesome", "wonderful", "incredible", "proud"]
    negative_words = ["hate", "bad", "sad", "terrible", "worst", "ugly", "boring", "gloomy", "disappointed", "fail"]
    
    sentiment_score = 0
    for word in text.split():
        if word in positive_words:
            sentiment_score += 1
        elif word in negative_words:
            sentiment_score -= 1
            
    if sentiment_score > 0:
        return "positive"
    elif sentiment_score < 0:
        return "negative"
    else:
        return "neutral"

def extract_hashtags(caption):
    if not isinstance(caption, str):
        return []
    return re.findall(r"#(\w+)", caption.lower())

def get_hashtag_frequency(df):
    all_hashtags = []
    for caption in df["caption"].dropna():
        all_hashtags.extend(extract_hashtags(caption))
    return Counter(all_hashtags)

def extract_keywords_frequency(df, num_keywords=5):
    all_words = []
    for caption in df["caption"].dropna():
        words = re.findall(r"\b\w+\b", caption.lower())
        # Simple stop word removal
        stop_words = set(["the", "a", "an", "is", "it", "in", "of", "and", "to", "for", "with", "on", "at", "by", "this", "that", "be", "from", "as", "i", "you", "he", "she", "we", "they", "my", "your", "his", "her", "our", "their", "was", "were", "had", "have", "has", "do", "does", "did", "will", "would", "can", "could", "should", "about", "out", "up", "down", "then", "there", "here", "when", "where", "why", "how", "what", "which", "who", "whom", "whose", "am", "are", "not", "no", "yes", "so", "but", "or", "if", "than", "than", "too", "very", "just", "only", "also", "much", "many", "some", "any", "all", "each", "every", "few", "more", "most", "other", "such", "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very", "s", "t", "can", "will", "just", "don", "should", "now"])
        all_words.extend([word for word in words if word not in stop_words and len(word) > 2])
    return Counter(all_words).most_common(num_keywords)

def train_engagement_prediction_model(df):
    # This function is kept as a placeholder. For truly offline and lightweight, 
    # a pre-trained simple model or rule-based system would be needed.
    # Given the constraint of no external models, this will just return None.
    print("Engagement prediction model training is not supported in offline mode without external libraries.")
    return None, None

# --- Visualizer Functions (from visualizer.py) ---
def plot_likes_comments_over_time(df, output_dir="./static/plots"):
    os.makedirs(output_dir, exist_ok=True)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values(by="timestamp")

    plt.figure(figsize=(12, 6))
    plt.plot(df["timestamp"], df["likes"], label="Likes")
    plt.plot(df["timestamp"], df["comments"], label="Comments")
    plt.xlabel("Date")
    plt.ylabel("Count")
    plt.title("Likes and Comments Over Time")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "likes_comments_over_time.png"))
    plt.close()

def plot_best_time_to_post(df, output_dir="./static/plots"):
    os.makedirs(output_dir, exist_ok=True)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["hour"] = df["timestamp"].dt.hour
    df["day_of_week"] = df["timestamp"].dt.day_name()

    # Average likes by hour
    avg_likes_by_hour = df.groupby("hour")["likes"].mean().reset_index()
    plt.figure(figsize=(10, 5))
    sns.barplot(x="hour", y="likes", data=avg_likes_by_hour)
    plt.xlabel("Hour of Day")
    plt.ylabel("Average Likes")
    plt.title("Average Likes by Hour of Day")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "avg_likes_by_hour.png"))
    plt.close()

    # Average likes by day of week
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    df["day_of_week"] = pd.Categorical(df["day_of_week"], categories=day_order, ordered=True)
    avg_likes_by_day = df.groupby("day_of_week")["likes"].mean().reset_index().sort_values("day_of_week")
    plt.figure(figsize=(10, 5))
    sns.barplot(x="day_of_week", y="likes", data=avg_likes_by_day)
    plt.xlabel("Day of Week")
    plt.ylabel("Average Likes")
    plt.title("Average Likes by Day of Week")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "avg_likes_by_day.png"))
    plt.close()

def plot_post_type_performance(df, output_dir="./static/plots"):
    os.makedirs(output_dir, exist_ok=True)
    post_type_performance = df.groupby("post_type")["likes"].mean().reset_index()

    fig = px.bar(post_type_performance, x="post_type", y="likes",
                 title="Average Likes by Post Type",
                 labels={"post_type": "Post Type", "likes": "Average Likes"})
    fig.write_image(os.path.join(output_dir, "post_type_performance.png"))

# --- Demo Data Function (from demo_data.py) ---
def create_demo_data():
    """Create demo Instagram data for testing the application"""
    
    # Sample Instagram posts data
    demo_posts = [
        {
            'post_id': 1,
            'caption': 'Amazing sunset at the beach! Perfect end to a wonderful day. #sunset #beach #nature #photography #peaceful',
            'likes': 1250,
            'comments': 89,
            'views': None,
            'post_type': 'image',
            'timestamp': datetime.datetime(2024, 1, 15, 18, 30)
        },
        {
            'post_id': 2,
            'caption': 'New workout routine is killing it! Feeling stronger every day 💪 #fitness #workout #motivation #health #gym',
            'likes': 890,
            'comments': 45,
            'views': None,
            'post_type': 'image',
            'timestamp': datetime.datetime(2024, 1, 16, 7, 15)
        },
        {
            'post_id': 3,
            'caption': 'Delicious homemade pasta tonight! Recipe in my stories 🍝 #cooking #pasta #homemade #foodie #italian',
            'likes': 2100,
            'comments': 156,
            'views': 5600,
            'post_type': 'video',
            'timestamp': datetime.datetime(2024, 1, 17, 19, 45)
        },
        {
            'post_id': 4,
            'caption': 'Monday blues hitting hard today. Need more coffee ☕ #monday #coffee #tired #work #mood',
            'likes': 567,
            'comments': 23,
            'views': None,
            'post_type': 'image',
            'timestamp': datetime.datetime(2024, 1, 22, 9, 30)
        },
        {
            'post_id': 5,
            'caption': 'Incredible concert last night! The energy was absolutely amazing 🎵 #concert #music #live #energy #amazing',
            'likes': 1890,
            'comments': 234,
            'views': 8900,
            'post_type': 'video',
            'timestamp': datetime.datetime(2024, 1, 23, 23, 15)
        },
        {
            'post_id': 6,
            'caption': 'Quiet morning with my book and tea. Sometimes the simple moments are the best ☕📚 #reading #tea #peaceful #morning #books',
            'likes': 1456,
            'comments': 67,
            'views': None,
            'post_type': 'image',
            'timestamp': datetime.datetime(2024, 1, 24, 8, 45)
        },
        {
            'post_id': 7,
            'caption': 'Terrible weather ruined our picnic plans. So disappointed 😞 #weather #rain #disappointed #plans #weekend',
            'likes': 234,
            'comments': 12,
            'views': None,
            'post_type': 'image',
            'timestamp': datetime.datetime(2024, 1, 25, 14, 20)
        },
        {
            'post_id': 8,
            'caption': 'New art project finished! Spent weeks on this painting 🎨 #art #painting #creative #artist #proud',
            'likes': 3200,
            'comments': 189,
            'views': 12000,
            'post_type': 'video',
            'timestamp': datetime.datetime(2024, 1, 26, 16, 30)
        },
        {
            'post_id': 9,
            'caption': 'Family dinner was perfect tonight. Love spending time with everyone ❤️ #family #dinner #love #together #grateful',
            'likes': 2890,
            'comments': 145,
            'views': None,
            'post_type': 'image',
            'timestamp': datetime.datetime(2024, 1, 27, 20, 15)
        },
        {
            'post_id': 10,
            'caption': 'Hiking adventure in the mountains! The views were breathtaking 🏔️ #hiking #mountains #adventure #nature #views',
            'likes': 4567,
            'comments': 298,
            'views': 15600,
            'post_type': 'video',
            'timestamp': datetime.datetime(2024, 1, 28, 15, 45)
        }
    ]
    
    return pd.DataFrame(demo_posts)

# --- Flask App Routes (from app.py) ---
@app.route('/')
def index():
    return send_file('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    global scraped_data
    username = request.json.get('username')
    
    if not username:
        return jsonify({'error': 'Username is required'}), 400
    
    try:
        # Check if demo mode (username is 'demo')
        if username.lower() == 'demo':
            scraped_data = create_demo_data()
        else:
            # Scrape Instagram data
            scraped_data = scrape_instagram_profile(username)
            
            if scraped_data.empty:
                return jsonify({'error': 'No data found for this username. Try "demo" for sample data.'}), 404
        
        # Perform analysis
        scraped_data['sentiment'] = scraped_data['caption'].apply(analyze_sentiment)
        hashtag_freq = get_hashtag_frequency(scraped_data)
        keywords = extract_keywords_frequency(scraped_data)
        
        # Generate visualizations
        plot_likes_comments_over_time(scraped_data)
        plot_best_time_to_post(scraped_data)
        plot_post_type_performance(scraped_data)
        
        # Train engagement prediction model (placeholder, no actual training)
        model, features = train_engagement_prediction_model(scraped_data)
        
        # Prepare response data
        response_data = {
            'total_posts': len(scraped_data),
            'avg_likes': scraped_data['likes'].mean(),
            'avg_comments': scraped_data['comments'].mean(),
            'sentiment_distribution': scraped_data['sentiment'].value_counts().to_dict(),
            'top_hashtags': dict(hashtag_freq.most_common(10)),
            'posts': scraped_data.to_dict('records')
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download_csv')
def download_csv():
    global scraped_data
    if scraped_data is None or scraped_data.empty:
        return jsonify({'error': 'No data available'}), 404
    
    csv_path = 'instagram_data.csv'
    scraped_data.to_csv(csv_path, index=False)
    return send_file(csv_path, as_attachment=True)

@app.route('/plots/<filename>')
def serve_plot(filename):
    return send_file(f'static/plots/{filename}')

if __name__ == '__main__':
    # Create static directories
    os.makedirs('static/plots', exist_ok=True)
    
    app.run(host='0.0.0.0', port=5000, debug=True)


