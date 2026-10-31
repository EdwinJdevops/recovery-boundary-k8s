FROM python:3.12-alpine@sha256:e6dae589c1c05976188fd3bd019afd091445fc533ed2ea29001beddc7368a9c8
WORKDIR /app
COPY index.html /app/index.html
USER 10001:10001
EXPOSE 8080
CMD ["python", "-m", "http.server", "8080", "--bind", "0.0.0.0"]
