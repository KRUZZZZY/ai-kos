compilation fails in main.adb 
because of potential aliasing problem detected
spark ada fails as well for the same reason:
gnatprove -P main.gpr --mode=flow

main.adb:9:13: error: writable actual for "X" overlaps with actual for "Y"
