import os
import io
import base64
import tempfile
import random
from datetime import datetime, timedelta
from collections import Counter
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import instaloader

app = Flask(__name__, static_folder='.')
app.config['SECRET_KEY'] = 'instagram_analyzer_secret_key'

# Enable CORS for all routes
CORS(app)

class InstagramAnalyzer:
    def __init__(self):
        self.loader = instaloader.Instaloader()
        # Disable downloading of posts, videos, etc.
        self.loader.download_pictures = False
        self.loader.download_videos = False
        self.loader.download_video_thumbnails = False
        self.loader.download_geotags = False
        self.loader.download_comments = False
        self.loader.save_metadata = False
        
    def extract_username(self, input_str):
        """Extract username from Instagram URL or return as-is if it's already a username"""
        input_str = input_str.strip()
        
        # If it's a URL, extract username
        if 'instagram.com' in input_str:
            # Handle various Instagram URL formats
            if '/p/' in input_str:
                # Post URL - extract username from the URL structure
                parts = input_str.split('/')
                if 'instagram.com' in parts:
                    idx = parts.index('instagram.com')
                    if idx + 1 < len(parts) and parts[idx + 1]:
                        return parts[idx + 1]
            else:
                # Profile URL
                parts = input_str.split('/')
                for i, part in enumerate(parts):
                    if 'instagram.com' in part and i + 1 < len(parts):
                        username = parts[i + 1]
                        # Remove query parameters
                        username = username.split('?')[0]
                        return username
        
        # If it's already a username (no URL), return as-is
        return input_str.replace('@', '')
    
    def get_profile_posts(self, username):
        """Get post metadata from Instagram profile"""
        try:
            profile = instaloader.Profile.from_username(self.loader.context, username)
            
            posts_data = []
            post_count = 0
            
            # Limit to recent posts to avoid rate limiting
            for post in profile.get_posts():
                if post_count >= 100:  # Limit to last 100 posts
                    break
                    
                post_data = {
                    'date': post.date_utc.strftime('%Y-%m-%d'),
                    'time': post.date_utc.strftime('%H:%M:%S'),
                    'datetime': post.date_utc,
                    'day_of_week': post.date_utc.strftime('%A'),
                    'hour': post.date_utc.hour,
                    'type': 'video' if post.is_video else 'image'
                }
                posts_data.append(post_data)
                post_count += 1
            
            return {
                'success': True,
                'username': username,
                'total_posts': len(posts_data),
                'posts': posts_data,
                'profile_info': {
                    'followers': profile.followers,
                    'following': profile.followees,
                    'total_posts': profile.mediacount
                }
            }
            
        except instaloader.exceptions.ProfileNotExistsException:
            return {'success': False, 'error': 'Profile not found'}
        except instaloader.exceptions.PrivateProfileNotFollowedException:
            return {'success': False, 'error': 'Profile is private'}
        except Exception as e:
            return {'success': False, 'error': f'Error fetching profile: {str(e)}'}
    
    def analyze_posting_patterns(self, posts_data):
        """Analyze posting patterns and generate visualizations"""
        if not posts_data:
            return {'success': False, 'error': 'No posts data to analyze'}
        
        df = pd.DataFrame(posts_data)
        
        # Day of week analysis
        day_counts = df['day_of_week'].value_counts()
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        day_counts = day_counts.reindex(day_order, fill_value=0)
        
        # Hour analysis
        hour_counts = df['hour'].value_counts().sort_index()
        
        # Generate charts
        charts = self.generate_charts(day_counts, hour_counts)
        
        return {
            'success': True,
            'day_analysis': day_counts.to_dict(),
            'hour_analysis': hour_counts.to_dict(),
            'charts': charts,
            'post_table': df[['date', 'time', 'day_of_week', 'type']].to_dict('records')
        }
    
    def generate_charts(self, day_counts, hour_counts):
        """Generate base64 encoded charts"""
        charts = {}
        
        # Set style
        plt.style.use('default')
        sns.set_palette("husl")
        
        # Day of week chart
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(day_counts.index, day_counts.values, color='skyblue', edgecolor='navy', alpha=0.7)
        ax.set_title('Posts by Day of Week', fontsize=16, fontweight='bold')
        ax.set_xlabel('Day of Week', fontsize=12)
        ax.set_ylabel('Number of Posts', fontsize=12)
        ax.tick_params(axis='x', rotation=45)
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                   f'{int(height)}', ha='center', va='bottom')
        
        plt.tight_layout()
        
        # Convert to base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        charts['day_chart'] = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        # Hour chart
        fig, ax = plt.subplots(figsize=(12, 6))
        bars = ax.bar(hour_counts.index, hour_counts.values, color='lightcoral', edgecolor='darkred', alpha=0.7)
        ax.set_title('Posts by Hour of Day', fontsize=16, fontweight='bold')
        ax.set_xlabel('Hour of Day', fontsize=12)
        ax.set_ylabel('Number of Posts', fontsize=12)
        ax.set_xticks(range(0, 24))
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                       f'{int(height)}', ha='center', va='bottom')
        
        plt.tight_layout()
        
        # Convert to base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        charts['hour_chart'] = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        return charts

def generate_mock_data():
    """Generate mock Instagram post data for testing"""
    posts_data = []
    
    # Generate 50 mock posts over the last 30 days
    base_date = datetime.now() - timedelta(days=30)
    
    for i in range(50):
        # Random date within last 30 days
        random_days = random.randint(0, 30)
        random_hours = random.randint(0, 23)
        random_minutes = random.randint(0, 59)
        
        post_date = base_date + timedelta(days=random_days, hours=random_hours, minutes=random_minutes)
        
        post_data = {
            'date': post_date.strftime('%Y-%m-%d'),
            'time': post_date.strftime('%H:%M:%S'),
            'datetime': post_date,
            'day_of_week': post_date.strftime('%A'),
            'hour': post_date.hour,
            'type': random.choice(['image', 'video'])
        }
        posts_data.append(post_data)
    
    return posts_data

def analyze_mock_patterns(posts_data):
    """Analyze mock posting patterns"""
    df = pd.DataFrame(posts_data)
    
    # Day of week analysis
    day_counts = df['day_of_week'].value_counts()
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    day_counts = day_counts.reindex(day_order, fill_value=0)
    
    # Hour analysis
    hour_counts = df['hour'].value_counts().sort_index()
    
    # Generate charts
    charts = generate_mock_charts(day_counts, hour_counts)
    
    return {
        'success': True,
        'day_analysis': day_counts.to_dict(),
        'hour_analysis': hour_counts.to_dict(),
        'charts': charts,
        'post_table': df[['date', 'time', 'day_of_week', 'type']].to_dict('records')
    }

def generate_mock_charts(day_counts, hour_counts):
    """Generate mock charts"""
    charts = {}
    
    # Set style
    plt.style.use('default')
    sns.set_palette("husl")
    
    # Day of week chart
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(day_counts.index, day_counts.values, color='skyblue', edgecolor='navy', alpha=0.7)
    ax.set_title('Posts by Day of Week (Demo Data)', fontsize=16, fontweight='bold')
    ax.set_xlabel('Day of Week', fontsize=12)
    ax.set_ylabel('Number of Posts', fontsize=12)
    ax.tick_params(axis='x', rotation=45)
    
    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
               f'{int(height)}', ha='center', va='bottom')
    
    plt.tight_layout()
    
    # Convert to base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
    buffer.seek(0)
    charts['day_chart'] = base64.b64encode(buffer.getvalue()).decode()
    plt.close()
    
    # Hour chart
    fig, ax = plt.subplots(figsize=(12, 6))
    bars = ax.bar(hour_counts.index, hour_counts.values, color='lightcoral', edgecolor='darkred', alpha=0.7)
    ax.set_title('Posts by Hour of Day (Demo Data)', fontsize=16, fontweight='bold')
    ax.set_xlabel('Hour of Day', fontsize=12)
    ax.set_ylabel('Number of Posts', fontsize=12)
    ax.set_xticks(range(0, 24))
    
    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        if height > 0:
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                   f'{int(height)}', ha='center', va='bottom')
    
    plt.tight_layout()
    
    # Convert to base64
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
    buffer.seek(0)
    charts['hour_chart'] = base64.b64encode(buffer.getvalue()).decode()
    plt.close()
    
    return charts

@app.route('/api/instagram/analyze', methods=['POST'])
def analyze_instagram():
    """Main endpoint for Instagram analysis"""
    try:
        data = request.get_json()
        if not data or 'username' not in data:
            return jsonify({'success': False, 'error': 'Username is required'}), 400
        
        analyzer = InstagramAnalyzer()
        username = analyzer.extract_username(data['username'])
        
        # Get posts data
        result = analyzer.get_profile_posts(username)
        if not result['success']:
            return jsonify(result), 400
        
        # Analyze patterns
        analysis = analyzer.analyze_posting_patterns(result['posts'])
        if not analysis['success']:
            return jsonify(analysis), 400
        
        # Combine results
        final_result = {
            'success': True,
            'username': result['username'],
            'total_posts_analyzed': result['total_posts'],
            'profile_info': result['profile_info'],
            'day_analysis': analysis['day_analysis'],
            'hour_analysis': analysis['hour_analysis'],
            'charts': analysis['charts'],
            'post_table': analysis['post_table']
        }
        
        return jsonify(final_result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Server error: {str(e)}'}), 500

@app.route('/api/instagram/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'Instagram Analyzer'})

@app.route('/api/test/demo', methods=['POST'])
def demo_analysis():
    """Demo endpoint with mock data"""
    try:
        # Generate mock data
        posts_data = generate_mock_data()
        
        # Analyze patterns
        analysis = analyze_mock_patterns(posts_data)
        
        # Create mock profile info
        mock_profile = {
            'followers': 150000000,  # 150M followers like Nike
            'following': 150,
            'total_posts': 5000
        }
        
        # Combine results
        result = {
            'success': True,
            'username': 'demo_account',
            'total_posts_analyzed': len(posts_data),
            'profile_info': mock_profile,
            'day_analysis': analysis['day_analysis'],
            'hour_analysis': analysis['hour_analysis'],
            'charts': analysis['charts'],
            'post_table': analysis['post_table']
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Demo error: {str(e)}'}), 500

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(path):
        return send_from_directory('.', path)
    else:
        if os.path.exists('index.html'):
            return send_from_directory('.', 'index.html')
        else:
            return "index.html not found", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

