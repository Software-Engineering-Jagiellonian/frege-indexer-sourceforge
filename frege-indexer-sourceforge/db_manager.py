import psycopg2
from config.config import config
from datetime import datetime


def connect():
    params = config("credentials.ini")
    engine = psycopg2.connect(**params)
    return engine


class DbManager:

    @staticmethod
    def save_repository(entry):
        if not entry:
            return
        connection = connect()
        try:
            print("Calling database")
            query = "INSERT INTO repositories (repo_id, git_url, repo_url, crawl_time) VALUES (%s, %s, %s, %s);"
            connection.cursor().execute(query, (entry['repo_id'], entry['git_url'], entry['repo_url'], datetime.now().astimezone().isoformat()))
        except (Exception, psycopg2.DatabaseError) as error:
            print("Error in transaction Reverting all other operations of a transaction ", error)
            connection.rollback()
            raise
        else:
            connection.commit()
            print("Transaction completed successfully")
        finally:
            if connection is not None:
                print("Closing connection to database")
                connection.close()
