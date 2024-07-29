FROM python:3.11.3

# to the terminal with out buffering it first
ENV PYTHONUNBUFFERED 1

# prevents python from writing pyc files to disk
ENV PYTHONDONTWRITEBYTECODE 1

WORKDIR /app
COPY poetry.lock pyproject.toml /app/

# install Python Dependencies
RUN pip3 install poetry==1.7.1
RUN poetry config virtualenvs.create false
RUN poetry install  --no-interaction

COPY . /app
RUN chmod +x /app/docker_entrypoint.sh

# Install cron
RUN apt-get update
RUN apt-get install -y cron
RUN apt-get install nano

RUN touch /var/log/cron.log

ENTRYPOINT /app/docker_entrypoint.sh && tail -f /var/log/cron.log
