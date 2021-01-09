import itertools
import os
import sys

from fregeindexerlib.database_connection import DatabaseConnectionParameters
from fregeindexerlib.indexer_type import IndexerType
from fregeindexerlib.rabbitmq_connection import RabbitMQConnectionParameters

from logger import logger
from single_page_projects_extractor import SinglePageProjectsExtractor
from single_project_code_url_exctractor import SingleProjectCodeUrlExtractor
from single_project_git_link_extractor import SingleProjectGitLinkExtractor
from single_project_git_url_extractor import SingleProjectGitUrlExtractor
from single_project_message_builder import SingleProjectRabbitMQMessageBuilder
from single_project_response_extractor import SingleProjectResponseExtractor
from source_forge_indexer import SourceforgeIndexer

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
                logger.info(f'Project {project_name} has children: {projects_url}')

                for url in projects_url:
                    git_url = singleProjectGitLinkExtractor.extract(url)
                    if git_url:
                        payload = singleProjectRabbitMQMessageBuilder.build(url, url[2:], git_url)
                        yield payload


def parse_environment(variable, optional=False, optional_value=None):
    try:
        return os.environ.get(variable, optional_value) if optional else os.environ[variable]
    except KeyError:
        logger.error(f'{variable} in environment var must be provided!')
        sys.exit(1)


if __name__ == '__main__':
    rabbitmq_host = parse_environment('RMQ_HOST')
    rabbitmq_port = int(parse_environment('RMQ_PORT', optional=True, optional_value='5672'))
    database_host = parse_environment('DB_HOST')
    database_name = parse_environment('DB_DATABASE')
    database_username = parse_environment('DB_USERNAME')
    database_password = parse_environment('DB_PASSWORD')

    rabbit = RabbitMQConnectionParameters(host=rabbitmq_host, port=rabbitmq_port)
    database = DatabaseConnectionParameters(host=database_host, database=database_name,
                                            username=database_username, password=database_password)
    sourceforge_iterator = run()

    app = SourceforgeIndexer(indexer_type=IndexerType.SOURCEFORGE, rabbitmq_parameters=rabbit,
                             database_parameters=database, rejected_publish_delay=10, iterator=sourceforge_iterator)

    app.run()
