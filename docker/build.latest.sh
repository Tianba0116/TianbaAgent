#!/bin/bash

unset KUBECONFIG

cd .. && docker build -f docker/Dockerfile.latest \
             -t Tianba0116/TianbaAgent .

docker tag Tianba0116/TianbaAgent Tianba0116/TianbaAgent:$(date +%y%m%d)