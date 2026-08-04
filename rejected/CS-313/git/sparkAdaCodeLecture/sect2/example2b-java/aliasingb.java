class aliasingb {

    public static void exchange(MyBool x,MyBool y){
        x.theBool = x.theBool ^ y.theBool;
        y.theBool = x.theBool ^ y.theBool;
        x.theBool = x.theBool ^ y.theBool;
    };

    public static void main(String[] args){
	    MyBool x = new MyBool(true);            
	    MyBool y = new MyBool(false);
            exchange(x,y);
	    System.out.println(x.theBool); /* false  - correct exchange */
	    System.out.println(y.theBool); /* true  - correct exchange */
	    x = new MyBool(true);            
            exchange(x,x);
	    System.out.println(x.theBool);  /* false - wrong exchange */
	    x = new MyBool(false);            
            exchange(x,x);
	    System.out.println(x.theBool);  /* false */
	}
}


class MyBool {
    public boolean theBool;

    MyBool (boolean x) { theBool = x;};
}
