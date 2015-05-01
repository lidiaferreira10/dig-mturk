#!/bin/sh

STAGING_AREA=$1
EXPERIMENT=$2
PROFILE_NAME=$3
AWS_KEY=$4
AWS_SECRET=$5

mvn exec:java -Dexec.mainClass="edu.isi.dig.mturk.hitFiles" -Dexec.cleanupDaemonThreads="false" -Dexec.args="$STAGING_AREA $EXPERIMENT $PROFILE_NAME $AWS_KEY $AWS_SECRET"
