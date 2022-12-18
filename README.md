# About The Project

File storage.
This project is focused on deploying on Google cloud.

## Installation

1. `python -m venv .venv`
2. `source .venv/bin/activate`
3. `pip install -r requirements.txt`

<p align="right">(<a href="#top">back to top</a>)</p>

## Usage

Bootstrap libraries won't be added to the project. Run `bash bin/download_bootstrap` to download bootstrap.

### Development

1. Create .env (`cp .env.template .env`) file with related environment variables
2. `python manage.py runserver` or `bash entrypoint.sh`
3. To run with Google cloud DB see [this](https://cloud.google.com/python/django/appengine#run-locally)

<p align="right">(<a href="#top">back to top</a>)</p>

### Google cloud

1. See [this](https://cloud.google.com/python/django/appengine)
2. To deploy: `bash bin/deploy` (gcloud and wget are needed).
3. Bootstrap should be placed to `base/static/bootstrap/` (deploy command includes this step),
libraries can't be downloaded from Google engine.
4. To resolve the CORS issues:
    - cp configurations/cors.json.template configurations/cors.json with needed values
    - gcloud storage buckets update gs://bucket-name --cors-file=configurations/cors.json

<p align="right">(<a href="#top">back to top</a>)</p>

## Testing

To run unit tests:
1. `export TRAMPOLINE_CI=1`
2. `python manage.py test`

## Migrations

For migrations, add `BF_ADMIN_USERNAME` and `BF_ADMIN_PASSWORD` to virtual environment to create admin user.
