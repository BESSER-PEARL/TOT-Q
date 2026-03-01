"""Definition of the agent properties within the ``gitlab_platform`` section:"""

from besser.agent.core.property import Property

SECTION_GITLAB = 'gitlab_platform'

GITLAB_PERSONAL_TOKEN = Property(SECTION_GITLAB, 'gitlab.personal_token', str, None)
"""
The Personal Access Token used to connect to the GitLab API

name: ``gitlab.personal_token``

type: ``str``

default value: ``None``
"""

GITLAB_WEBHOOK_TOKEN = Property(SECTION_GITLAB, 'gitlab.webhook_token', str, None)
"""
The secret token defined at the webhook creation

name: ``gitlab.webhook_token``

type: ``str``

default value: ``None``
"""

GITLAB_WEBHOOK_PORT = Property(SECTION_GITLAB, 'gitlab.webhook_port', int, 8901)
"""
The server local port. This port should be exposed of proxied to make it visible by GitLab

name: ``gitlab.webhook_port``

type: ``int``

default value: ``8901``
"""
