set EXPERIMENT=%1
mvn exec:java -Dexec.mainClass="edu.isi.dig.mturk.consolidateResults" -Dexec.cleanupDaemonThreads="false" -Dexec.args="%EXPERIMENT%"