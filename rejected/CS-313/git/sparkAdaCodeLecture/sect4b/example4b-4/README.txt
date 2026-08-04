gnatmake exchange_and_count.adb
  succeeds without errors

gnatprove -P main.gpr --mode=flow
reports errors discussed in the lecture:

exchange_and_count.ads:5:34: warning: unused initial value of "Z"
    5 |procedure Exchange_And_Count(X,Y,Z : in out Integer)
      |                                 ^ here

exchange_and_count.ads:8:08: medium: missing dependency "null => Z"
    8>|  with Depends => (X => Y,
    9 |                   Y => X,
   10 |                   Z => Z);

exchange_and_count.ads:10:20: medium: missing dependency "Z => X"
   10 |                   Z => Z);
      |                   ^ here

exchange_and_count.ads:10:25: medium: incorrect dependency "Z => Z"
   10 |                   Z => Z);
      |                        ^ here

