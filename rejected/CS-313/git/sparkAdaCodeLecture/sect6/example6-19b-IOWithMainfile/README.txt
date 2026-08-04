gnatmake main.adb
gnatprove -P main.gpr --proof=progressive
   both succeed
-------------------

This is an adaption of sect6/example6-19 for testing
whether the installation works and getting started.

Download the files
   * Easiest done by downloading the zip archive. 
     * Choose the Ark-Linux application (similar to win-zip) for extracting the files
     * Use Extract to
     * Select a directory (the system displays the whole file system which includes all students
          find your user name (usually your student number), create a directory inside for
          extracting it to, and extract it to it
   * You can as well manually move the files into a directory of your choice

Open the file browser Dolphin (it is in the start menu)
Navigate to the directory where you have put the files.
If you click on 

  main.gpr

the gps system should start (it might take initially some time because initialization 
   takes some time, later it will be faster)

see screenshot 
screenshots/GPSscreenshot.png

(it's important to have the  shell, so that I can make some error
diagnosis, if there are problems)


If you then go to subdirectory 

gnatprove

and click on 

example.mlw

then a shall from which why3 is started should open
(it's important to have the  shell, so that I can make some error
diagnosis, if there are problems)

see screenshot 
screenshots/why3screenshot.png




This file contains a wrapper class for IO
as_io_wrapper.ads and
as_io_wrapper.adb

which makes use of spark ada files
spark.ads
spark-text_io.ads
spark-text_io.adb
spark-text_io-integer_io.ads
spark-text_io-integer_io.adb

which are adaptions from files obtained as part of the distribution located at
/opt/spark2014/share/examples/spark/spark_io/
or
/usr/gnat/share/examples/spark/spark_io/

It contains two very simple examples for using it:

test_integer_io.ads 
test_string_io.ads




