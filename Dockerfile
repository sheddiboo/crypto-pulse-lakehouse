# Pulls the official AWS Lambda Python base image
FROM public.ecr.aws/lambda/python:3.12

# Injects the ultra-fast uv package manager into the container
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
# Copies only the dependency definitions to leverage Docker layer caching
COPY pyproject.toml uv.lock ./

# Installs dependencies globally since Lambda environments do not use virtual environments
RUN uv pip install --system -r pyproject.toml

# Copies the actual ingestion logic into the execution directory
COPY src/lambda_function.py ${LAMBDA_TASK_ROOT}

# Instructs the Lambda runtime on exactly which function to execute
CMD [ "lambda_function.lambda_handler" ]