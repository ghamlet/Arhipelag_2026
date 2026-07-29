#!/bin/bash

DRONE_VISION_VERSION=${1:-1.0.0}

docker run -it \
           --privileged \
           --rm \
           -v /dev/video0:/dev/video0 \
           "drone_vision:$DRONE_VISION_VERSION"
