public class arrayProblem{
    student[] studentArray = new student[10];
   
    void init(person[] myarray){
	myarray[0] = new person();
    };

    arrayProblem(){
	init(studentArray);
    };

    public static void main(String[] args){
	student[] studentArray = new arrayProblem().studentArray;
	};
};
	
class person{}

class student extends person {}

