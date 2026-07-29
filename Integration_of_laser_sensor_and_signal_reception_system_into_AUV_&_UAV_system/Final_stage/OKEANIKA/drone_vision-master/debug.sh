#!/bin/bash

DRONE_VISION_VERSION=${1:-1.0.0}
shift

docker run -it \
           --privileged \
           --rm \
           -v /dev/video0:/dev/video0 \
           -v "$(pwd)/models:/drone_vision/models" \
           -v "$(pwd)/output:/drone_vision/output" \
           -v "$(pwd)/scripts:/drone_vision/scripts" \
           "drone_vision:$DRONE_VISION_VERSION" "$@"
