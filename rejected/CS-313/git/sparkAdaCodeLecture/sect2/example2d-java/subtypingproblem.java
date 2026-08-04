public class subtypingproblem{
    student myStudent = new student(1);
   
    void init(person myperson){
        myperson = new person();
    };

    subtypingproblem(){
        init(myStudent);
    };

    public static void main(String[] args){
        Integer x = new subtypingproblem().myStudent.studnr;
        System.out.println(x);
        // prints out 1, since Student1 since not changed by init.
        };
};
        
class person{}

class student extends person {
    Integer studnr;
    student(Integer nr){
        this.studnr = nr;
            }
 }

