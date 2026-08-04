This library has two improvements as suggested by Finley Bennet
Usage:
    Use the files from lib/asLibraryIO/    and replace the two files
    as_io_wrapper.ads and as_io_wrapper.adb by the files from this directory  

Improvements of this library:

  * There is a procedure AS_Skip_Line which is a wrapper for Ada.Text_IO.Skip_Line
    In case the problem occurs that after an As_Get the next As_Get takes the rest
    of the input, then As_Skip_Line; could be used before the As_Get to clear the buffer.
    We haven't been able to reproduce this particular error, and haven't tested this function yet.

    Both this and the old version of the asLibraryIO has as well a procedure
       AS_Clear_Buffer;
    which I used in the past to achieve the same effect, namely to clear the input buffer,
    but was doing it in a more adhoc way, whereas  AS_Skip_Line uses the procedure Skip_Line; 
    provided by Ada for this purpose.

 *  In As_Get(Item : out Integer,...)   there was a bug that if the user enteres an empty string the
    system crashes. Now a length check has been added so that if the input consists of blanks only 
    it asks the  user to try again.

