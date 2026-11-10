int acumular(int n, bool ativo) {
    int total;
    if (ativo) {
        total = 0;
    } else {
        return 0;
    }
    while (n > 0) {
        int proximo = total + n;
        total = proximo;
        n = n - 1;
    }
    return total;
}

void mostrar(int valor) {
    print(valor);
}

int main() {
    int x = acumular(3, true);
    {
        bool x = false;
        print(x);
    }
    mostrar(x);
    return 0;
}
