#!/bin/bash

set -e

DRONE_VISION_VERSION=${1:-1.0.0}

docker buildx create --name pibuilder --node pibuilder0 --use
docker buildx inspect --bootstrap

docker buildx build --builder pibuilder \
                    --output type=docker,dest="build/drone_vision:$DRONE_VISION_VERSION.amd64.tar" \
                    --progress=plain \
                    --platform linux/amd64 \
                    --tag "drone_vision:$DRONE_VISION_VERSION" \
                    .

docker buildx build --builder pibuilder \
                    --output type=docker,dest="build/drone_vision:$DRONE_VISION_VERSION.arm64.tar" \
                    --progress=plain \
                    --platform linux/arm64 \
                    --tag "drone_vision:$DRONE_VISION_VERSION" \
                    .

gzip -9f "build/drone_vision:$DRONE_VISION_VERSION.amd64.tar"
gzip -9f "build/drone_vision:$DRONE_VISION_VERSION.arm64.tar"

gunzip -c "build/drone_vision:$DRONE_VISION_VERSION.amd64.tar.gz" | docker load
