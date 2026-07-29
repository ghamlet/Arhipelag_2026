#!/bin/bash

set -e

DRONE_VISION_VERSION=${1:-1.0.0}

gunzip -c "drone_vision:$DRONE_VISION_VERSION.arm64.tar.gz" | docker load
docker rm -f drone_vision
docker run -d \
           --name drone_vision \
           --privileged \
           --restart=always \
           -v /dev/video0:/dev/video0 \
           "drone_vision:$DRONE_VISION_VERSION"
