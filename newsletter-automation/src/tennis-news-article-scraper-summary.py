import os
import requests
from bs4 import BeautifulSoup
from typing import List, Dict
import google.generativeai as genai
import pandas as pd
import json
import traceback
import re

def estimate_reading_time(text: str) -> int:
    """
    Estimate reading time based on word count
    Average reading speed is around 250 words per minute
    
    :param text: Article text
    :return: Estimated reading time in minutes
    """
    # Remove extra whitespace and split into words
    words = re.findall(r'\w+', text)
    word_count = len(words)
    reading_time = max(1, round(word_count / 250))
    return reading_time

class ArticleSummarizer:
    def __init__(self, gemini_api_key: str):
        """
        Initialize the article summarizer with Gemini API
        
        :param gemini_api_key: Google Gemini API key
        """
        # Configure Gemini API
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def extract_article_content(self, url: str) -> Dict:
        """
        Extract article content using requests and BeautifulSoup
        
        :param url: URL of the article
        :return: Dictionary with article details
        """
        try:
            # Use a user agent to mimic a browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # Fetch the page
            response = requests.get(url, headers=headers)
            
            # Check if request was successful
            if response.status_code != 200:
                print(f"Failed to retrieve {url}. Status code: {response.status_code}")
                return None
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title
            title = soup.find('h1')
            title = title.text.strip() if title else 'No Title'
            
            # Extract main content (this will vary by website)
            # For BBC, you might need to inspect the specific article page structure
            content_paragraphs = soup.find_all(['p', 'article'])
            
            # Combine text from paragraphs
            text = ' '.join([p.get_text().strip() for p in content_paragraphs if p.get_text().strip()])
            
            # Check if text is empty
            if not text:
                print(f"No text extracted from {url}")
                return None
            
            # Estimate reading time
            reading_time = estimate_reading_time(text)
            
            return {
                'url': url,
                'title': title,
                'text': text,
                'reading_time': reading_time,
                'source': url.split('/')[2]  # Extract domain
            }
        
        except Exception as e:
            print(f"Error extracting {url}:")
            print(traceback.format_exc())
            return None

    def summarize_with_gemini(self, article_text: str, custom_title: str = None) -> str:
        """
        Summarize article text using Gemini API
        
        :param article_text: Full text of the article
        :param custom_title: Optional custom title provided by user
        :return: Concise summary
        """
        try:
            # Truncate very long articles
            max_tokens = 10000
            truncated_text = article_text[:max_tokens]
            
            # Incorporate custom title if provided
            title_context = f"Article Title: {custom_title}" if custom_title else ""
            
            prompt = f"""{title_context}
            Please provide a summary of the following article text for my tennis newsletter. 
            The summary should be no more than 1 paragraph and around 3-4 sentences, capturing the key points and main message. Here is an example summary:

            British number one Katie Boulter will climb into the world's top 25 for the first time after reaching the final of the Hong Kong Open. She eventually lost in the final to Russian top seed Diana Shnaider 6-2 6-1 and missed out on a third WTA title of the year. Boulter is next set to represent Great Britain at the Billie Jean King Cup Finals on 15 November.

            Article text: 
            {truncated_text}
            """
            
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Summarization error: {e}")
            print(traceback.format_exc())
            return "Unable to generate summary"

    def process_urls(self, urls: List[str], custom_titles: List[str] = None) -> List[Dict]:
        """
        Process multiple URLs and generate summaries
        
        :param urls: List of article URLs
        :param custom_titles: Optional list of custom titles
        :return: List of summarized articles
        """
        summarized_articles = []
        
        # If no custom titles provided, use None for each URL
        if custom_titles is None:
            custom_titles = [None] * len(urls)
        
        for url, custom_title in zip(urls, custom_titles):
            # Extract article content
            article_details = self.extract_article_content(url)
            
            if article_details and article_details['text']:
                # Generate summary with optional custom title
                summary = self.summarize_with_gemini(article_details['text'], custom_title)
                
                # Combine details with summary
                article_details['summary'] = summary
                summarized_articles.append(article_details)
            else:
                print(f"Could not extract content from {url}")
        
        return summarized_articles

    def save_to_mailchimp_format(self, articles: List[Dict], filename: str = 'mailchimp_article_summaries.txt'):
        """
        Save summarized articles in a format easy to copy-paste into Mailchimp
        
        :param articles: List of article dictionaries
        :param filename: Output text filename
        """
        with open(filename, 'w', encoding='utf-8') as f:
            for article in articles:
                f.write(f"Title: {article['title']}\n")
                f.write(f"Summary: {article['summary']}\n")
                f.write(f"Reading Time: {article['reading_time']} min\n")
                f.write(f"Full Article: {article['url']}\n\n")
        
        print(f"Saved {len(articles)} articles to {filename}")
        
        # Also print to console for immediate review
        with open(filename, 'r', encoding='utf-8') as f:
            print(f.read())

def main():
    # Replace with your actual Gemini API key
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'AIzaSyBrss_ENXnmWFSZR3v17HBjbFXlzYrfXUE')
    
    # Prompt user for URLs
    print("Enter article URLs (press Enter without typing to finish):")
    urls_to_scrape = [
        'https://www.bbc.co.uk/sport/tennis/articles/c8rl1671z7jo'
    ]
    titles = [
        ''
    ]
    
    while True:
        url = input("URL: ").strip()
        if not url:
            break
        
        # Optional custom title input
        title = input("Custom Title (optional, press Enter to skip): ").strip() or None
        
        urls_to_scrape.append(url)
        titles.append(title)
    
    # Initialize summarizer
    summarizer = ArticleSummarizer(GEMINI_API_KEY)
    
    # Process URLs
    summarized_articles = summarizer.process_urls(urls_to_scrape, titles)
    
    # Save results
    if summarized_articles:
        summarizer.save_to_mailchimp_format(summarized_articles)
    else:
        print("No articles were successfully processed.")

if __name__ == "__main__":
    main()