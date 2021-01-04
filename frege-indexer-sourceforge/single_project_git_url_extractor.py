import requests
from bs4 import BeautifulSoup


class SingleProjectGitUrlExtractor:

    @staticmethod
    def extract(soup):
        if not soup:
            return

        print('Looking for project children (GIT)')
        code_urls = set()
        for li in soup.find_all('ul', {'class': 'dropdown'})[0]('li'):
            try:
                a = li('a')[0]
                if a('span')[0].text.startswith('Git'):
                    href_link = a['href']
                    if href_link.startswith('/p'):
                        url = f'https://sourceforge.net/{href_link[1:]}'

                        print(f'Found project GIT children on {url}, scrapping')
                        response = requests.get(url)
                        soup = BeautifulSoup(response.text, 'html.parser')

                        for link in soup.find_all('div', {'class': 'list card'}):
                            cleaned_link = link('a')[0]['href']
                            if cleaned_link.startswith('/p'):
                                code_urls.add(cleaned_link[1:])
            except:
                pass

        if code_urls:
            print(f'Found project GIT children: {code_urls}')
        return code_urls
