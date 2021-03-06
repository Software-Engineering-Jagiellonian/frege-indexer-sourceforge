from logger import logger


class SingleProjectCodeUrlExtractor:

    @staticmethod
    def extract(soup):
        if not soup:
            return

        logger.info('Looking for project children (CODE)')
        code_urls = set()
        for span in soup.find_all('span'):
            if span.text == 'Code':
                code_urls.add(span.find_parents('a')[0]['href'][1:])

        if code_urls:
            logger.info(f'Found project CODE children: {code_urls}')
        return code_urls
