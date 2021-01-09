import requests
from bs4 import BeautifulSoup

from logger import logger


class SingleProjectResponseExtractor:

    @staticmethod
    def extract(project_name):
        if not project_name:
            return

        url = f'https://sourceforge.net/{project_name}'
        logger.info(f'Getting project from: {url}')
        response = requests.get(url)
        return BeautifulSoup(response.text, 'html.parser')