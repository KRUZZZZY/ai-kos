gnatmake main.adb
gnatprove -P main.gpr --proof=progressive
  both succeed
--------------------------------------------
This file contains a very simple toy example of a critical system,
a cooling system of a nuclear power station.
What it does is it asks for the temperature, and if it exceeds a critical
value, the cooling system is set to activated.

The runnable file is called main
which makes use of the package 
cooling_system_nuclear_power



This file uses the wrapper class for IO
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




