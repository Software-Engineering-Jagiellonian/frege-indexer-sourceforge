## Frege Indexer Sourceforge
### Overview
Indexer of repositories from https://sourceforge.net/. It scrappes this website in order to find all git repositories that share the code publicly.
When found said repository the information about the repository are both send to RabbitMQ queue and saved to database.

### Environment variables
In order to run this application locally it's required to supply it with below environment variables:

`RMQ_HOST` - The RabbitMQ host

`RMQ_PORT` - RabbitMQ port (if not specified default port 5672 is used)

`DB_HOST` - PostgreSQL server host

`DB_DATABASE` - Database name

`DB_USERNAME` - Database username

`DB_PASSWORD` - Database password
