import requests
from urllib.parse import urljoin, urlparse
from datetime import datetime, timedelta
import json
import os
from typing import List, Dict
import mailchimp_marketing as MailchimpMarketing
from mailchimp_marketing.api_client import ApiClientError
from newspaper import Article
from bs4 import BeautifulSoup

class TennisNewsletterAutomator:
    def __init__(self, mailchimp_api_key: str = None, mailchimp_list_id: str = None):
        """Initialize with optional Mailchimp credentials"""
        if mailchimp_api_key and mailchimp_list_id:
            self.mailchimp = MailchimpMarketing.Client()
            self.mailchimp.set_config({
                "api_key": mailchimp_api_key,
                "server": mailchimp_api_key.split('-')[-1]
            })
            self.list_id = mailchimp_list_id
        else:
            self.mailchimp = None
            self.list_id = None

    def fetch_tennis_news(self, days_back: int = 14) -> List[Dict]:
        """
        Fetch recent tennis news from multiple sources
        Returns list of articles with title, url, summary, and source
        """
        # Define more robust sources with base URLs
        sources = [
            {
                "base_url": "https://www.atptour.com",
                "news_url": "https://www.atptour.com/en/news/",
                "article_selector": "a.article-item"
            },
            {
                "base_url": "https://www.wtatennis.com",
                "news_url": "https://www.wtatennis.com/news",
                "article_selector": "a.article-link"
            }
        ]
        
        articles = []
        for source in sources:
            try:
                response = requests.get(source['news_url'])
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find article links
                article_links = soup.select(source['article_selector'])
                
                for link in article_links[:5]:  # Limit to 5 articles per source
                    # Construct full URL
                    href = link.get('href', '')
                    full_url = urljoin(source['base_url'], href)
                    
                    try:
                        article = Article(full_url)
                        article.download()
                        article.parse()
                        article.nlp()  # Generate summary
                        
                        articles.append({
                            'title': article.title,
                            'url': full_url,
                            'summary': article.summary,
                            'source': source['base_url'],
                            'date': article.publish_date or datetime.now()
                        })
                    except Exception as article_error:
                        print(f"Error processing article {full_url}: {article_error}")
                
            except Exception as e:
                print(f"Error fetching from {source['news_url']}: {str(e)}")
                
        return articles

    def generate_newsletter_draft(self, articles: List[Dict]) -> str:
        """
        Generate HTML content for newsletter from articles
        """
        html_content = f"""
        <html>
        <body>
            <h1>Tennis News Roundup</h1>
            <p>Latest tennis stories from {datetime.now().strftime('%B %d, %Y')}:</p>
            
            {''.join([f"""
            <div style="margin-bottom: 20px; border-bottom: 1px solid #ccc;">
                <h2><a href="{article['url']}">{article['title']}</a></h2>
                <p><em>Source: {article['source']}</em></p>
                <p>{article['summary']}</p>
            </div>
            """ for article in articles])}
        </body>
        </html>
        """
            
        return html_content

    def print_articles(self, articles: List[Dict]):
        """
        Print articles to console for verification
        """
        for article in articles:
            print(f"Title: {article['title']}")
            print(f"URL: {article['url']}")
            print(f"Summary: {article['summary'][:200]}...")
            print("---")

def main():
    # No Mailchimp credentials required for initial testing
    automator = TennisNewsletterAutomator()
    
    # Fetch recent tennis news
    articles = automator.fetch_tennis_news()
    
    # Print articles to verify
    automator.print_articles(articles)
    
    # Optional: Generate HTML draft
    html_content = automator.generate_newsletter_draft(articles)
    
    # Optionally save HTML to file
    with open('newsletter_draft.html', 'w') as f:
        f.write(html_content)

if __name__ == "__main__":
    main()