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
