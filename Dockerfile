# jupyter base image
FROM quay.io/jupyter/scipy-notebook:lab-4.1.5

# install python libraries available in conda
RUN mamba install --yes \
    'geopandas=0.14.3' \
    'treelib=1.7.0' && \
    mamba clean --all -f -y && \
    fix-permissions "${CONDA_DIR}" && \
    fix-permissions "/home/${NB_USER}"