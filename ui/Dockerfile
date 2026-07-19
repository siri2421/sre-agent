# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install python dependencies
COPY app/requirements.txt app_requirements.txt
COPY ui/requirements.txt ui_requirements.txt
RUN pip install --no-cache-dir -r app_requirements.txt -r ui_requirements.txt

# Copy repository code (app, skills, ui)
COPY . /app

# Expose Cloud Run default port
EXPOSE 8080

# Set pythonpath so app.config and root modules resolve cleanly
ENV PYTHONPATH=/app

# Run Streamlit on port 8080 for Cloud Run
CMD ["streamlit", "run", "ui/streamlit_app.py", "--server.port=8080", "--server.address=0.0.0.0", "--server.headless=true"]
