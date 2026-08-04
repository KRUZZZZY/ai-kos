This is the corrected version of the aliasing problem example for
exchanging two variables.
It only carries out the exchange if X and Y are not equal.


compilation fails in main.adb 
because of potential aliasing problem detected
spark ada fails as well for the same reason:
gnatprove -P main.gpr --mode=flow

main.adb:9:13: error: writable actual for "X" overlaps with actual for "Y"
