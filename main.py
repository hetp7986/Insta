import instaloader
import re
import csv
from datetime import datetime
from collections import Counter, defaultdict
import statistics
import matplotlib.pyplot as plt

def extract_username(url):
    match = re.search(r"instagram\.com/([^/?#&]+)", url)
    return match.group(1) if match else None

def fetch_posts(username):
    L = instaloader.Instaloader()
    try:
        profile = instaloader.Profile.from_username(L.context, username)
        posts = list(profile.get_posts())
        follower_count = profile.followers
        return posts, follower_count
    except Exception as e:
        print(f"[❌ ERROR] Unable to fetch posts: {e}")
        return [], 0

def format_post_details(posts):
    detailed_output = []
    csv_data = [["Post #", "Date", "Time (UTC)", "Likes", "Comments", "Views", "Caption", "URL"]]

    for i, post in enumerate(posts):
        date_str = post.date_utc.strftime('%Y-%m-%d')
        time_str = post.date_utc.strftime('%H:%M:%S')
        caption = (post.caption or "").replace('\n', ' ')[:120]
        views = post.video_view_count if post.is_video else 'N/A'

        detailed_output.append(
            f"📌 Post {i + 1}:\n"
            f"  - Date: {date_str}\n"
            f"  - Time: {time_str} UTC\n"
            f"  - Likes: {post.likes}\n"
            f"  - Comments: {post.comments}\n"
            f"  - Views: {views}\n"
            f"  - URL: {post.url}\n"
        )

        csv_data.append([f"Post {i + 1}", date_str, time_str, post.likes, post.comments, views, caption, post.url])
    return detailed_output, csv_data

def analyze_schedule(posts):
    day_hour_counter = defaultdict(list)
    for post in posts:
        weekday = post.date_utc.strftime('%A')
        hour = post.date_utc.hour
        day_hour_counter[weekday].append(hour)

    print("\n📈 Posting Schedule (Most Frequent Times):")
    suggestion_times = []
    for day, hours in day_hour_counter.items():
        if hours:
            most_common_hour = statistics.mode(hours)
            print(f"  {day}: around {most_common_hour}:00 UTC")
            suggestion_times.append((day, most_common_hour))
    return suggestion_times

def generate_suggestions(suggestion_times, user_posts_per_day):
    hour_counter = Counter([hour for _, hour in suggestion_times])
    best_hours = [hour for hour, _ in hour_counter.most_common(user_posts_per_day)]
    print("\n🎯 Suggested Posting Plan for You:")
    for i, hour in enumerate(best_hours, 1):
        print(f"  - Suggested Time {i}: {hour}:00 UTC")
    return best_hours

def save_csv(data, filename="detailed_post_data.csv"):
    with open(filename, "w", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(data)
    print(f"\n[📄] CSV saved as: {filename}")

def main():
    print("=== Instagram Competitor Analyzer v2 ===")
    url = input("Enter Instagram profile URL: ").strip()
    username = extract_username(url)
    if not username:
        print("[❌] Invalid URL.")
        return

    posts, followers = fetch_posts(username)
    if not posts:
        return

    print(f"[✅] {len(posts)} posts fetched. Showing post details...\n")
    detailed_output, csv_data = format_post_details(posts)

    for line in detailed_output:
        print(line)

    suggestion_times = analyze_schedule(posts)

    try:
        user_posts = int(input("\nHow many times do you want to post in one day? (1-5): ").strip())
    except:
        user_posts = 1

    if user_posts > 5: user_posts = 5
    generate_suggestions(suggestion_times, user_posts)

    save_opt = input("\nDo you want to save the data as CSV? (y/n): ").strip().lower()
    if save_opt == 'y':
        save_csv(csv_data)

if __name__ == "__main__":
    main()
