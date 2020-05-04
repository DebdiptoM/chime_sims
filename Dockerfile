FROM continuumio/miniconda3
WORKDIR /chime_sims

# Install gcc for compiling gvar later
RUN apt-get update && apt-get -y install gcc

RUN conda update -yq -n base -c defaults conda
RUN conda create -yq -n chime_sims python=3.7 pip pandas matplotlib scipy numpy seaborn

# Activate new environment which has numpy
RUN echo "source activate chime_sims" > ~/.bashrc
ENV PATH /opt/conda/envs/chime_sims/bin:$PATH

# And install dependencies
COPY ./requirements.txt .
RUN pip install -q -r requirements.txt
