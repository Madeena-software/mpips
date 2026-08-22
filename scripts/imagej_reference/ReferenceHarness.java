import ij.ImagePlus;
import ij.plugin.ContrastEnhancer;
import ij.plugin.filter.RankFilters;
import ij.process.ByteProcessor;
import ij.process.ImageProcessor;
import ij.process.ShortProcessor;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.Scanner;
import mpicbg.ij.clahe.FastFlat;
import mpicbg.ij.clahe.Flat;

/** Thin adapter: all image algorithms remain in the pinned external artifacts. */
public class ReferenceHarness {
    static int[] values(int n) {
        int[] a = new int[n];
        Scanner s = new Scanner(System.in);
        for (int i = 0; i < n; i++) a[i] = s.nextInt();
        return a;
    }

    static ImageProcessor processor(String dtype, int w, int h, int[] v) {
        if (dtype.equals("uint8")) {
            byte[] p = new byte[v.length];
            for (int i = 0; i < p.length; i++) p[i] = (byte)v[i];
            return new ByteProcessor(w, h, p, null);
        }
        short[] p = new short[v.length];
        for (int i = 0; i < p.length; i++) p[i] = (short)v[i];
        return new ShortProcessor(w, h, p, null);
    }

    static int selectorForKernel(int kernel) {
        switch (kernel) {
            case 3: return 1;
            case 5: return 3;
            case 7: return 5;
            default: throw new IllegalArgumentException("kernel must be 3, 5, or 7");
        }
    }

    static void hybrid(ImageProcessor ip, int kernel, int repetitions) throws Exception {
        int selector = selectorForKernel(kernel);
        double nsize = (selector - 1) / 2.0;
        Hybrid_2D_Median_Filter plugin = new Hybrid_2D_Median_Filter();
        ImagePlus imp = new ImagePlus("fixture", ip);
        Field stack = plugin.getClass().getDeclaredField("stack");
        stack.setAccessible(true); stack.set(plugin, imp.getStack());
        Field atebit = plugin.getClass().getDeclaredField("atebit");
        atebit.setAccessible(true); atebit.setBoolean(plugin, ip instanceof ByteProcessor);
        Field times = plugin.getClass().getDeclaredField("times");
        times.setAccessible(true); times.setDouble(plugin, repetitions);
        Field size = plugin.getClass().getDeclaredField("nsize");
        size.setAccessible(true); size.setDouble(plugin, nsize);
        Field title = plugin.getClass().getDeclaredField("otitle");
        title.setAccessible(true); title.set(plugin, "fixture");
        Method m = plugin.getClass().getDeclaredMethod("Hybrid2dMedianizer", ImagePlus.class, double.class);
        m.setAccessible(true);
        ImagePlus out = (ImagePlus)m.invoke(plugin, imp, nsize);
        emit(out.getProcessor());
    }

    static void emit(ImageProcessor ip) {
        Object pixels = ip.getPixels();
        if (pixels instanceof byte[]) {
            for (byte x : (byte[])pixels) System.out.print((x & 255) + " ");
        } else {
            for (short x : (short[])pixels) System.out.print((x & 65535) + " ");
        }
    }

    public static void main(String[] args) throws Exception {
        String op = args[0], dtype = args[1];
        int w = Integer.parseInt(args[2]), h = Integer.parseInt(args[3]);
        ImageProcessor ip = processor(dtype, w, h, values(w * h));
        switch (op) {
            case "stretch":
                ContrastEnhancer stretch = new ContrastEnhancer();
                stretch.setNormalize(true); // MPIPS characterizes normalized pixel data.
                stretch.stretchHistogram(ip, Double.parseDouble(args[4]));
                emit(ip); break;
            case "equalize_weighted":
                new ContrastEnhancer().equalize(ip); emit(ip); break;
            case "equalize_classic":
                ContrastEnhancer classic = new ContrastEnhancer();
                Field ce = ContrastEnhancer.class.getDeclaredField("classicEqualization");
                ce.setAccessible(true); ce.setBoolean(classic, true);
                classic.equalize(ip); emit(ip); break;
            case "circular":
                new RankFilters().rank(ip, Double.parseDouble(args[4]), RankFilters.MEDIAN);
                emit(ip); break;
            case "hybrid":
                hybrid(ip, Integer.parseInt(args[4]), Integer.parseInt(args[5])); break;
            case "clahe_flat":
            case "clahe_fast":
                ImagePlus imp = new ImagePlus("fixture", ip);
                int blockRadius = Integer.parseInt(args[4]);
                int internalBins = Integer.parseInt(args[5]);
                float slope = Float.parseFloat(args[6]);
                if (op.equals("clahe_flat")) Flat.getInstance().run(imp, blockRadius, internalBins, slope, null, true);
                else FastFlat.run(imp, blockRadius, internalBins, slope, null);
                emit(imp.getProcessor()); break;
            default: throw new IllegalArgumentException(op);
        }
        System.exit(0); // ImageJ 1.x may leave non-daemon executor threads alive.
    }
}
