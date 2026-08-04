This example demonstrates that X'Old can only occur for an input or input/output parameter
It fails flow analysis, and should do so as discussed in the lecture.

gnatmake example.adb
  succeeds
gnatprove -P main.gpr --mode=flow

causes an error

example.ads:15:15: high: "M" is not initialized at subprogram entry
   15 |  Post => M = M'Old;
      |              ^ here

The reason is that M is an out parameter, so there is no initial value of M.

