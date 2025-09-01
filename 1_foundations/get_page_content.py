import requests

class PageContentFetcher:
    def get_page_content(self, url):
        response = requests.get(url)
        if response.status_code == 200:
            return response.text
        else:
            return f"Failed to retrieve page. Status code: {response.status_code}"