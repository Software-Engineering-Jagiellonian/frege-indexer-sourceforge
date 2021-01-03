import itertools
import os
import re
import sys
from typing import Optional

import requests
from bs4 import BeautifulSoup
from fregeindexerlib.crawl_result import CrawlResult
from fregeindexerlib.database_connection import DatabaseConnectionParameters
from fregeindexerlib.indexer import Indexer
from fregeindexerlib.indexer_type import IndexerType
from fregeindexerlib.rabbitmq_connection import RabbitMQConnectionParameters


class SinglePageProjectsExtractor:

    @staticmethod
    def extract(page_number):
        if page_number <= 0:
            return
        url = f'https://sourceforge.net/directory/?sort=popular&page={page_number}'
        print(f'Scrapping: {url}')
        response = requests.get(url)

        if response.status_code == 404:
            print('Response returned 404 Not Found - end of scrapping')
            return None

        soup = BeautifulSoup(response.text, 'html.parser')

        projects_set = set()
        for link in soup.find_all('a', href=re.compile(r'/projects/\w+')):
            projects_set.add('/'.join(link['href'].split('/')[:3])[1:])

        print(f'Found projects: {projects_set}')
        return projects_set


class SingleProjectResponseExtractor:

    @staticmethod
    def extract(project_name):
        if not project_name:
            return

        url = f'https://sourceforge.net/{project_name}'
        print(f'Getting project from: {url}')
        response = requests.get(url)
        return BeautifulSoup(response.text, 'html.parser')


class SingleProjectCodeUrlExtractor:

    @staticmethod
    def extract(soup):
        if not soup:
            return

        print('Looking for project children (CODE)')
        code_urls = set()
        for span in soup.find_all('span'):
            if span.text == 'Code':
                code_urls.add(span.find_parents('a')[0]['href'][1:])

        if code_urls:
            print(f'Found project CODE children: {code_urls}')
        return code_urls


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


class SingleProjectGitLinkExtractor:

    @staticmethod
    def extract(code_url):
        if not code_url:
            return

        url = f'https://sourceforge.net/{code_url}'
        print(f'Looking for git clone url on {url}')
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        value = soup.find('input', {'id': 'access_url'})
        if value:
            value = value.get('value')
            if value.startswith('git clone'):
                git_link = value.split()[2]
                print(f'Found git clone link: {git_link}')
                return git_link


class SingleProjectRabbitMQMessageBuilder:

    @staticmethod
    def build(code_url, project_name, git_url):
        if not project_name or not git_url:
            return

        message = dict()

        message['repo_url'] = f'https://sourceforge.net/{code_url}'
        message['repo_id'] = project_name
        message['git_url'] = git_url

        return message


singlePageProjectsExtractor = SinglePageProjectsExtractor()
singleProjectCodeUrlExtractor = SingleProjectCodeUrlExtractor()
singleProjectGitLinkExtractor = SingleProjectGitLinkExtractor()
singleProjectRabbitMQMessageBuilder = SingleProjectRabbitMQMessageBuilder()
singleProjectResponseExtractor = SingleProjectResponseExtractor()
singleProjectGitUrlExtractor = SingleProjectGitUrlExtractor()


def run():
    while True:
        for i in itertools.count(start=1):
            projects = singlePageProjectsExtractor.extract(i)
            if not projects:
                yield None

            for project_name in projects:
                single_project_soup = singleProjectResponseExtractor.extract(project_name)

                project_code_url = singleProjectCodeUrlExtractor.extract(single_project_soup)
                project_git_ulr = singleProjectGitUrlExtractor.extract(single_project_soup)

                projects_url = project_git_ulr | project_code_url
                print(f'Project {project_name} has children: {projects_url}')

                for url in projects_url:
                    git_url = singleProjectGitLinkExtractor.extract(url)
                    if git_url:
                        payload = singleProjectRabbitMQMessageBuilder.build(url, url[2:], git_url)
                        yield payload


if __name__ == '__main__':

    try:
        rabbitmq_host = os.environ['RABBITMQ_HOST']
    except KeyError:
        print("RabbitMQ host must be provided as RABBITMQ_HOST environment var!")
        sys.exit(1)

    try:
        rabbitmq_port = int(os.environ.get('RABBITMQ_PORT', '5672'))
    except ValueError:
        print("RABBITMQ_PORT must be an integer")
        sys.exit(2)

    try:
        queue = os.environ['QUEUE']
    except KeyError:
        print("Destination queue must be provided as QUEUE environment var!")
        sys.exit(3)


    class SourceforgeIndexer(Indexer):
        def crawl_next_repository(self, prev_repository_id: Optional[str]) -> Optional[CrawlResult]:
            result = next(sourceforge_iterator)
            print(result)
            return CrawlResult(
                result['repo_id'],
                result['repo_url'],
                result['git_url'],
                None)


    sourceforge_iterator = run()

    rabbit = RabbitMQConnectionParameters(host=rabbitmq_host, port=rabbitmq_port)
    database = DatabaseConnectionParameters(host="localhost", database="frege",
                                            username="postgres", password="admin")

    app = SourceforgeIndexer(indexer_type=IndexerType.SOURCEFORGE, rabbitmq_parameters=rabbit,
                             database_parameters=database, rejected_publish_delay=10)

    app.run()
