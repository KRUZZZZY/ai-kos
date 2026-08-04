This shows that from a files with "spark_mode(on)" one cannot call
a file with "spark_mode(off)"
This happens in this example with
main.adb (sparkmode on) calling exchange in example.adb (sparkmode off)

both
gnatprove -P main.gpr --proof=per_path
and
gnatprove -P main.gpr --mode=flow

give errors:

main.adb:13:04: error: "Exchange" is not allowed in SPARK
main.adb:29:04: warning: actuals for this call may be in wrong order [-gnatw.p]
main.adb:29:04: error: "Exchange" is not allowed in SPARK

