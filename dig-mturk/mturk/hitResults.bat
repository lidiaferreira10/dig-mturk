set STAGING_AREA=%1
set EXPERIMENT=%2
mvn exec:java -Dexec.mainClass="edu.isi.dig.mturk.hitResults" -Dexec.cleanupDaemonThreads="false" -Dexec.args="%STAGING_AREA% %EXPERIMENT%"