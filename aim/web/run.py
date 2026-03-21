import os

from aim.web.configs import AIM_SECRET_KEY

if not os.environ.get(AIM_SECRET_KEY):
    raise RuntimeError(
        'AIM_SECRET_KEY environment variable is required. '
        'Set it before starting: export AIM_SECRET_KEY=your-secret-key'
    )

from aim.web.api import create_app

app = create_app()
