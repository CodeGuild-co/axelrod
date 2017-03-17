FROM python:3.6-onbuild

CMD ["gunicorn", "web:app", "--worker-class", "gevent", "--log-file", "-", "--bind", "0.0.0.0:80", "--no-sendfile"]
