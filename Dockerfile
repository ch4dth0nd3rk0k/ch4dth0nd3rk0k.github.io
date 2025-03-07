# jupyter base image
FROM quay.io/jupyter/scipy-notebook:lab-4.1.5 AS jupyter

# install python libraries available in conda
RUN mamba install --yes \
    'jupyterlab-spellchecker=0.8.4' && \
    mamba clean --all -f -y && \
    fix-permissions "${CONDA_DIR}" && \
    fix-permissions "/home/${NB_USER}"

# install pip only libraries
RUN pip install git+https://github.com/DiogenesAnalytics/blog_utils

# test base image
FROM python:3.11 AS testing

# define the build arguments
ARG DCKRSRC

# install necessary dependencies
RUN apt-get update \
    && apt-get install -y \
      bash \
      git \
      gnupg \
      make \
      rsync \
      tree \
      wget \
      unzip \
      ruby \
      ruby-dev \
      build-essential \
    && rm -rf /var/lib/apt/lists/*

# Add the safe.directory config for Git
RUN git config --global --add safe.directory '*'

# Install Jekyll (no need for Bundler or a Gemfile)
RUN gem install jekyll -v 4.2.0

# download and install Google Chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" \
    >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# set workdir
WORKDIR ${DCKRSRC}

# copy source
COPY . .

# install requirements (installs sbase)
RUN pip3 install -r tests/requirements.txt

# get chromedriver (sbase installed by requirements.txt)
RUN sbase install chromedriver
