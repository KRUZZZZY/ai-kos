gnatmake test_integer_io.adb
gnatmake test_string_io.adb
gnatprove -P main.gpr --proof=progressive
  all succeed

---

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




