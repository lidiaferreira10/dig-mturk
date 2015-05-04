#!/bin/sh

STAGING_AREA=$1
EXPERIMENT=$2

mvn exec:java -Dexec.mainClass="edu.isi.dig.mturk.hitResults" -Dexec.cleanupDaemonThreads="false" -Dexec.args="$STAGING_AREA $EXPERIMENT"
