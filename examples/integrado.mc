bool marca() { print("chamada"); return true; }
int main() { int x=0; while (x<3) { print(x*8); x=x+1; } bool b=true || marca(); print(b); return x; }
