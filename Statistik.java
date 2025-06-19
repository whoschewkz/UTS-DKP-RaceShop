import java.util.Scanner;

public class Statistik {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        
        final int MAX_SIZE = 100; 
        double[] isi = new double[MAX_SIZE];
        double total = 0.0;
        double maks = Double.NEGATIVE_INFINITY;
        int n = 0;

        while (sc.hasNextDouble() && n < MAX_SIZE) {
            isi[n] = sc.nextDouble();
            total += isi[n];
            if (isi[n] > maks) {
                maks = isi[n];
            }
            n++;
        }
        sc.close();

        if (n > 0) {
            double ratarata = hitungRataRata(total, n);
            System.out.println("Rata-rata: " + ratarata);
            System.out.println("Nilai Maksimum: " + maks);
        } else {
            System.out.println("Tidak ada input.");
        }
    }

    static double hitungRataRata(double total, int n) {
        if (n == 0) return 0.0;
        return total / n;
    }
}
