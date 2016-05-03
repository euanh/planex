#!/usr/bin/env bash

set -xe

export PLANEX_CONTAINER=planex-master:latest
cd ..
mkdir SPECS
ln -s ../planex/planex.spec SPECS/planex.spec
planex/docker/planex-container planex-init
planex/docker/planex-container planex-pin add SPECS/planex.spec planex#HEAD
mkdir mock
ln -s /etc/mock/default.cfg mock/
ln -s /etc/mock/logging.ini mock/
planex/docker/planex-container make
