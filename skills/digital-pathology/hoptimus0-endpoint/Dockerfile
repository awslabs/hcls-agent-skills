ARG REGION=us-east-1

FROM 763104351884.dkr.ecr.${REGION}.amazonaws.com/pytorch-inference:2.5.1-gpu-py311-cu124-ubuntu22.04-sagemaker

RUN pip install --no-cache-dir timm huggingface_hub

COPY inference.py /opt/ml/model/code/inference.py

ENV SAGEMAKER_SUBMIT_DIRECTORY=/opt/ml/model/code
ENV SAGEMAKER_PROGRAM=inference.py
ENV SAGEMAKER_MODEL_SERVER_WORKERS=1
