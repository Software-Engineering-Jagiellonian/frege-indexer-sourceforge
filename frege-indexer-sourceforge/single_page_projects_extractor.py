import re

import requests
from bs4 import BeautifulSoup

from logger import logger


class SinglePageProjectsExtractor:

    @staticmethod
    def extract(page_number):
        if page_number <= 0:
            return
        url = f'https://sourceforge.net/directory/?sort=popular&page={page_number}'
        logger.info(f'Scrapping: {url}')
        response = requests.get(url)

        if response.status_code == 404:
            logger.info('Response returned 404 Not Found - end of scrapping')
            return None

        soup = BeautifulSoup(response.text, 'html.parser')

        projects_set = set()
        for link in soup.find_all('a', href=re.compile(r'/projects/\w+')):
            projects_set.add('/'.join(link['href'].split('/')[:3])[1:])

        logger.info(f'Found projects: {projects_set}')
        return projects_set
