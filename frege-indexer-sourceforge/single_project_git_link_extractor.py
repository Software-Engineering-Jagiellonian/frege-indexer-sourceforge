import requests
from bs4 import BeautifulSoup

from logger import logger


class SingleProjectGitLinkExtractor:

    @staticmethod
    def extract(code_url):
        if not code_url:
            return

        url = f'https://sourceforge.net/{code_url}'
        logger.info(f'Looking for git clone url on {url}')
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        value = soup.find('input', {'id': 'access_url'})
        if value:
            value = value.get('value')
            if value.startswith('git clone'):
                git_link = value.split()[2]
                logger.info(f'Found git clone link: {git_link}')
                return git_link
