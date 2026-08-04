This is the example with added main.adb file, 
  which uses the Ada IO library. 

gnatmake main.adb
  succeeds

This file doesn't pass Spark ada checks because it doesn't use
the Spark Ada IO library.


