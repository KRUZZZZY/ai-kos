class exchangeOfValueParameters{
 
    public static void exchange(int a, int b){
        int tmp = a;
        a = b;
        b = tmp;}

    public static void exchange(myint a, myint b){
        myint tmp = a;
        a = b;
        b = tmp;
}

    public static void exchange1(myint a, myint b){
        myint tmp = new myint(a.theint);
        a.theint = b.theint;
        b.theint = tmp.theint;
}

    public static void main(String[] args){
        int a = 5;
        int b = 7;
        exchange(a,b);
        System.out.println(a);
        System.out.println(b);
        myint x = new myint(5);
        myint y = new myint(7);
        exchange(x,y);
        System.out.println(x.theint);
        System.out.println(y.theint);
        exchange1(x,y);
        System.out.println(x.theint);
        System.out.println(y.theint);

    };
} 
 

class myint{
    public int theint ;
    public myint(int theint){
        this.theint = theint;}
}
        
        
