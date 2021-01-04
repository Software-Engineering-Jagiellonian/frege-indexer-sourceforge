from typing import Optional

from fregeindexerlib import Indexer, CrawlResult, IndexerType, RabbitMQConnectionParameters, \
    DatabaseConnectionParameters


class SourceforgeIndexer(Indexer):

    def __init__(self, indexer_type: IndexerType, rabbitmq_parameters: RabbitMQConnectionParameters,
                 database_parameters: DatabaseConnectionParameters, rejected_publish_delay: int,
                 iterator):
        super().__init__(indexer_type, rabbitmq_parameters, database_parameters, rejected_publish_delay)
        self.iterator = iterator

    def crawl_next_repository(self, prev_repository_id: Optional[str]) -> Optional[CrawlResult]:
        result = next(self.iterator)
        return CrawlResult(
            result['repo_id'],
            result['repo_url'],
            result['git_url'],
            None)