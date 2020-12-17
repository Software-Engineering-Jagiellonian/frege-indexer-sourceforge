import os
import sys
import time

import pika as pika
import requests
import re
from bs4 import BeautifulSoup
import json
import itertools
from db_manager import DbManager


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
            sys.exit(0)

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
    def build(project_name, git_url):
        if not project_name or not git_url:
            return

        message = dict()

        message['repo_id'] = f'sourceforge-{project_name}'
        message['git_url'] = git_url

        return json.dumps(message)


class SingleProjectDatabaseEntryBuilder:

    @staticmethod
    def build(project_name, git_url):
        if not project_name or not git_url:
            return

        entry = dict()

        entry['repo_id'] = f'sourceforge-{project_name}'
        entry['git_url'] = git_url
        entry['repo_url'] = f'https://sourceforge.net/p/{project_name}'

        return entry


class RabbitMQConnectionHandler:

    @staticmethod
    def connect(rabbitmq_host, rabbitmq_port, queue_name):
        while True:
            try:
                print(f'Connecting to RabbitMQ ({rabbitmq_host}:{rabbitmq_port})')
                connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbitmq_host, port=rabbitmq_port))
                channel = connection.channel()
                channel.confirm_delivery()
                channel.queue_declare(queue=queue_name, durable=True)

                print('Connected')
                return channel
            except pika.exceptions.AMQPConnectionError as exception:
                print(f'AMQP Connection Error: {exception}')
                print('Sleeping for 10 seconds and retrying')
                time.sleep(10)
            except KeyboardInterrupt:
                print('Exiting')
                try:
                    connection.close()
                except NameError:
                    pass
                sys.exit(0)


class RabbitMQMessagePublisher:

    @staticmethod
    def publish(channel, payload):
        if not payload:
            return
        while True:
            try:
                print(f'Publishing message: {payload} to RabbitMQ')
                channel.basic_publish(exchange='',
                                      routing_key=queue,
                                      properties=pika.BasicProperties(delivery_mode=2),  # make message persistent
                                      body=bytes(payload, encoding='utf8'))
                print("Message was received by RabbitMQ")
                break
            except pika.exceptions.NackError:
                print("Message was REJECTED by RabbitMQ, sleeping for 10 seconds")
                time.sleep(10)


singlePageProjectsExtractor = SinglePageProjectsExtractor()
singleProjectCodeUrlExtractor = SingleProjectCodeUrlExtractor()
singleProjectGitLinkExtractor = SingleProjectGitLinkExtractor()
singleProjectRabbitMQMessageBuilder = SingleProjectRabbitMQMessageBuilder()
rabbitMQMessagePublisher = RabbitMQMessagePublisher()
rabbitMQConnectionHandler = RabbitMQConnectionHandler()
singleProjectResponseExtractor = SingleProjectResponseExtractor()
singleProjectGitUrlExtractor = SingleProjectGitUrlExtractor()
singleProjectDatabaseEntryBuilder = SingleProjectDatabaseEntryBuilder()
dbManager = DbManager()


def run(rabbitmq_host, rabbitmq_port, queue_name):
    while True:
        channel = rabbitMQConnectionHandler.connect(rabbitmq_host, rabbitmq_port, queue_name)

        for i in itertools.count(start=1):
            for project_name in singlePageProjectsExtractor.extract(i):
                single_project_soup = singleProjectResponseExtractor.extract(project_name)

                project_code_url = singleProjectCodeUrlExtractor.extract(single_project_soup)
                project_git_ulr = singleProjectGitUrlExtractor.extract(single_project_soup)

                projects_url = project_git_ulr | project_code_url
                print(f'Project {project_name} has children: {projects_url}')

                for url in projects_url:
                    git_url = singleProjectGitLinkExtractor.extract(url)
                    payload = singleProjectRabbitMQMessageBuilder.build(url[2:], git_url)
                    rabbitMQMessagePublisher.publish(channel, payload)

                    entry = singleProjectDatabaseEntryBuilder.build(url[2:], git_url)
                    dbManager.save_repository(entry)


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

    # todo - jakoś chyba by się przydalo zapisywac stan w jakim jestesmy (numer strony?) zeby w razie czego nie
    #  zaczynac od nowa -- nice to have not required
    run(rabbitmq_host, rabbitmq_port, queue)
