class aliasingbRepaired {

    public static void exchange(MyBool x,MyBool y){
        if (x != y) {
	    x.theBool = x.theBool ^ y.theBool;
	    y.theBool = x.theBool ^ y.theBool;
	    x.theBool = x.theBool ^ y.theBool;}
    };

    public static void main(String[] args){
	    MyBool x = new MyBool(true);            
	    MyBool y = new MyBool(false);
            exchange(x,y);
	    System.out.println(x.theBool); /* correct exchange - false  */
	    System.out.println(y.theBool); /* correct exchange - true */
	    x = new MyBool(true);            
            exchange(x,x);
	    System.out.println(x.theBool);  /* correct exchange - true */
	    x = new MyBool(false);            
            exchange(x,x);
	    System.out.println(x.theBool); /* correct exchange - false */
	}
}


class MyBool {
    public boolean theBool;

    MyBool (boolean x) { theBool = x;};
}
