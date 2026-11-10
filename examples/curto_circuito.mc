bool marca() {
    print("M");
    return true;
}

int main() {
    int a = 3;
    int b = 2;
    if (a < b && marca()) {
        print("ramo verdadeiro");
    }
    bool x = a < b || marca();
    print(x);
    return 0;
}
