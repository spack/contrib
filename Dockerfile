FROM bitnami/minideb:stretch

# docker build -t spack/contrib .

LABEL "com.github.actions.name"="Contributions over Time"
LABEL "com.github.actions.description"="A GitHub action to make a stacked area plot of contributions over time."
LABEL "com.github.actions.icon"="bar-chart"
LABEL "com.github.actions.color"="blue"

ENV PATH /opt/conda/bin:${PATH}
ENV LANG C.UTF-8
RUN /bin/bash -c "install_packages wget git ca-certificates gnupg2 && \
    wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh && \
    bash Miniconda3-latest-Linux-x86_64.sh -b -p /opt/conda && \
    rm Miniconda3-latest-Linux-x86_64.sh && \
    conda install -y -c conda-forge numpy matplotlib"

WORKDIR /code
COPY . /code
RUN pip install . \
  && chmod u+x /code/entrypoint.sh
ENTRYPOINT ["/code/entrypoint.sh"]
