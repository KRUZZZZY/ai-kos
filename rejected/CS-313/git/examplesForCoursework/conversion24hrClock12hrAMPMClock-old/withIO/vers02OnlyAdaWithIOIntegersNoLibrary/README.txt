This is the example with added IO for tyring out, which uses the Ada IO
 library. 

gnatmake main.adb
  succeeds

This file doesn't pass Spark ada checks because it doesn't use
the Spark Ada IO library.

vers03 will be the adjustment which passes as well Spark Ada checks.

