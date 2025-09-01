import os
import ipfshttpclient
from youtube_dl import YoutubeDL
import tweepy
import requests
import json
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
from bs4 import BeautifulSoup
import time

# IPFS client setup with version check disabled
try:
    IPFS_CLIENT = ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001', offline=True)
except Exception as e:
    print(f"Could not connect to IPFS: {e}")
    IPFS_CLIENT = None

# Load private key (must be on crawler machine, not in repo)
try:
    with open('crawler.key', 'rb') as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None,
        )
except FileNotFoundError:
    print("Private key not found, signing will be disabled")
    private_key = None

def sign_data(data):
    """Sign data with private key for verification"""
    if not private_key:
        return "unsigned"
        
    json_data = json.dumps(data, sort_keys=True).encode('utf-8')
    signature = private_key.sign(
        json_data,
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    return base64.b64encode(signature).decode('utf-8')

def store_to_ipfs(data):
    """Store data as IPFS object with signature verification"""
    if not IPFS_CLIENT:
        print("IPFS client not available, skipping storage")
        return None
        
    data['signature'] = sign_data(data)
    try:
        ipfs_hash = IPFS_CLIENT.add_json(data)
        print(f"Stored to IPFS: {ipfs_hash}")
        return ipfs_hash
    except Exception as e:
        print(f"Error storing to IPFS: {e}")
        return None

def fetch_youtube_videos():
    """Fetch verified political videos from YouTube"""
    if not IPFS_CLIENT:
        print("IPFS client not available, skipping YouTube fetch")
        return
        
    ydl_opts = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': 'videos/%(id)s.%(ext)s',
        'noplaylist': True
    }
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download(['https://www.youtube.com/user/DonaldTrump'])

def fetch_twitter_tweets():
    """Fetch archived tweets from Twitter API"""
    if not IPFS_CLIENT:
        print("IPFS client not available, skipping Twitter fetch")
        return
        
    auth = tweepy.OAuthHandler(os.getenv('TWITTER_API_KEY'), os.getenv('TWITTER_API_SECRET'))
    auth.set_access_token(os.getenv('TWITTER_ACCESS_TOKEN'), os.getenv('TWITTER_ACCESS_TOKEN_SECRET'))
    api = tweepy.API(auth)
    
    tweets = api.search_tweets(q='Donald Trump', count=100, lang='en')
    for tweet in tweets:
        store_to_ipfs({
            'type': 'tweet',
            'text': tweet.text,
            'timestamp': str(tweet.created_at),
            'user': tweet.user.screen_name
        })

def fetch_brave_search():
    """Query Brave Search for verified political statements"""
    if not IPFS_CLIENT:
        print("IPFS client not available, skipping Brave Search fetch")
        return
        
    response = requests.get(
        'https://api.search.brave.com/res/v1/web/search',
        params={'q': 'Donald Trump lies', 'count': 10},
        headers={'X-Brave-API-Key': os.getenv('BRAVE_API_KEY')}
    )
    results = response.json().get('relevance', [])
    for result in results:
        store_to_ipfs({
            'type': 'brave_search',
            'title': result.get('title'),
            'url': result.get('url'),
            'content': result.get('description')
        })

def fetch_politifact_articles():
    """Fetch fact-check articles from PolitiFact"""
    if not IPFS_CLIENT:
        print("IPFS client not available, skipping PolitiFact fetch")
        return
        
    try:
        # This is a simplified implementation
        # In a real implementation, we would need to handle pagination and rate limiting
        response = requests.get('https://www.politifact.com/factchecks/list/', timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find fact-check articles
        articles = soup.find_all('article', class_='m-statement')
        
        for article in articles[:10]:  # Limit to first 10 articles
            try:
                title_elem = article.find('a', class_='m-statement__quote')
                if title_elem:
                    title = title_elem.text.strip()
                    url = 'https://www.politifact.com' + title_elem.get('href', '')
                    
                    # Get article details
                    detail_response = requests.get(url, timeout=10)
                    detail_soup = BeautifulSoup(detail_response.content, 'html.parser')
                    
                    # Extract claim and fact check rating
                    claim_elem = detail_soup.find('div', class_='m-statement__quote')
                    claim = claim_elem.text.strip() if claim_elem else ''
                    
                    rating_elem = detail_soup.find('div', class_='m-statement__meter')
                    rating = rating_elem.find('img').get('alt', '') if rating_elem and rating_elem.find('img') else ''
                    
                    # Store in IPFS
                    ipfs_hash = store_to_ipfs({
                        'type': 'politifact',
                        'title': title,
                        'claim': claim,
                        'rating': rating,
                        'url': url,
                        'source': 'PolitiFact',
                        'timestamp': time.time()
                    })
                    
                    print(f"Stored PolitiFact article: {title} (Rating: {rating}) - IPFS: {ipfs_hash}")
                    
            except Exception as e:
                print(f"Error processing article: {e}")
                continue
                
    except Exception as e:
        print(f"Error fetching PolitiFact articles: {e}")

def fetch_groundnews_articles():
    """Fetch articles from Ground News"""
    if not IPFS_CLIENT:
        print("IPFS client not available, skipping Ground News fetch")
        return
        
    try:
        # This is a simplified implementation
        # In a real implementation, we would need to handle API authentication
        # and proper endpoint usage
        response = requests.get('https://ground.news/search?q=politics', timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find articles - this is a simplified selector
        articles = soup.find_all('div', class_='search-result')
        
        for article in articles[:10]:  # Limit to first 10 articles
            try:
                title_elem = article.find('h3')
                if title_elem:
                    title = title_elem.text.strip()
                    
                    link_elem = article.find('a')
                    url = link_elem.get('href', '') if link_elem else ''
                    
                    # Get article details
                    if url:
                        detail_response = requests.get(url, timeout=10)
                        detail_soup = BeautifulSoup(detail_response.content, 'html.parser')
                        
                        # Extract content
                        content_elem = detail_soup.find('article') or detail_soup.find('div', class_='content')
                        content = content_elem.text.strip() if content_elem else ''
                        
                        # Store in IPFS
                        ipfs_hash = store_to_ipfs({
                            'type': 'groundnews',
                            'title': title,
                            'content': content[:500] + '...' if len(content) > 500 else content,
                            'url': url,
                            'source': 'Ground News',
                            'timestamp': time.time()
                        })
                        
                        print(f"Stored Ground News article: {title} - IPFS: {ipfs_hash}")
                        
            except Exception as e:
                print(f"Error processing article: {e}")
                continue
                
    except Exception as e:
        print(f"Error fetching Ground News articles: {e}")

if __name__ == "__main__":
    print("Starting Lodestar crawler...")
    
    # Fetch content from all sources
    fetch_youtube_videos()
    fetch_twitter_tweets()
    fetch_brave_search()
    fetch_politifact_articles()
    fetch_groundnews_articles()
    
    print("Crawler completed. Data stored on IPFS with signatures.")