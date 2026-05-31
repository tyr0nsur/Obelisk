import ghidra.app.decompiler.DecompileOptions;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.listing.Program;

public class DumpFuObjectArrayWindows extends GhidraScript {
    private static final String SCRIPT_VERSION = "2026-05-31.1";

    private static final class Window {
        final String label;
        final long start;
        final long end;

        Window(String label, long start, long end) {
            this.label = label;
            this.start = start;
            this.end = end;
        }
    }

    private final Window[] windows = new Window[] {
        new Window("static_init_caller", 0x7a2780L, 0x7a27d8L),
        new Window("ctor_helper", 0x1d474e0L, 0x1d47640L),
        new Window("alloc_helper", 0x1d475a0L, 0x1d476d0L),
        new Window("reset_helper", 0x1d476e0L, 0x1d477d0L),
        new Window("destructor_finalizer", 0x1d58fb0L, 0x1d59050L),
        new Window("serial_accessor_a", 0x1d56970L, 0x1d56a26L),
        new Window("serial_accessor_b", 0x1d56d60L, 0x1d56ecdL),
    };

    @Override
    public void run() throws Exception {
        Program program = currentProgram;
        DecompInterface decompiler = new DecompInterface();
        DecompileOptions options = new DecompileOptions();
        try {
            decompiler.setOptions(options);
            if (!decompiler.openProgram(program)) {
                throw new IllegalStateException(
                    "failed to open program in decompiler: " + decompiler.getLastMessage());
            }

            println("script=DumpFuObjectArrayWindows.java");
            println("script_version=" + SCRIPT_VERSION);
            println("program=" + program.getName());
            println("language=" + program.getLanguageID());
            println("image_base=" + program.getImageBase());
            println("executable_sha256=" + program.getExecutableSHA256());
            println("window_count=" + windows.length);
            println("status=candidate-only static orientation");
            println("not_artifact_gate=true");
            println("promotion_ready=false");
            println("non_claim=Ghidra windows are offline navigation only; not consume or promote evidence");
            validatePreflight(program);
            for (Window window : windows) {
                println("window_spec=" + window.label + " start=0x" + Long.toHexString(window.start)
                    + " end=0x" + Long.toHexString(window.end));
            }

            for (Window window : windows) {
                dumpWindow(program, decompiler, window);
            }
        } finally {
            decompiler.dispose();
        }
    }

    private void validatePreflight(Program program) {
        for (String rawArg : getScriptArgs()) {
            String[] parts = rawArg.split("=", 2);
            if (parts.length != 2) {
                throw new IllegalArgumentException("preflight_failed: invalid_arg=" + rawArg);
            }
            String key = parts[0].trim();
            String expected = parts[1].trim();
            if (key.equals("expected_sha256")) {
                String actualSha256 = program.getExecutableSHA256();
                if (actualSha256 == null) {
                    throw new IllegalStateException("preflight_failed: expected_sha256 actual=<missing>");
                }
                requireEquals(key, expected.toLowerCase(), actualSha256.toLowerCase());
            } else if (key.equals("expected_language")) {
                requireEquals(key, expected, program.getLanguageID().toString());
            } else if (key.equals("expected_image_base")) {
                long expectedImageBase = parseExpectedLong(expected);
                if (expectedImageBase == 0) {
                    throw new IllegalStateException("preflight_failed: expected_image_base must_not_be_zero");
                }
                requireEquals(key, expectedImageBase, program.getImageBase().getOffset());
            } else if (key.equals("expected_window_count")) {
                requireEquals(key, Integer.parseInt(expected), windows.length);
            } else {
                throw new IllegalArgumentException("preflight_failed: unknown_arg=" + key);
            }
        }
        println("preflight=ok");
    }

    private static long parseExpectedLong(String value) {
        if (value.startsWith("0x") || value.startsWith("0X")) {
            return Long.parseUnsignedLong(value.substring(2), 16);
        }
        return Long.parseLong(value);
    }

    private static void requireEquals(String key, String expected, String actual) {
        if (!expected.equals(actual)) {
            throw new IllegalStateException(
                "preflight_failed: " + key + " expected=" + expected + " actual=" + actual);
        }
    }

    private static void requireEquals(String key, long expected, long actual) {
        if (expected != actual) {
            throw new IllegalStateException(
                "preflight_failed: " + key + " expected=0x" + Long.toHexString(expected)
                    + " actual=0x" + Long.toHexString(actual));
        }
    }

    private static void requireEquals(String key, int expected, int actual) {
        if (expected != actual) {
            throw new IllegalStateException(
                "preflight_failed: " + key + " expected=" + expected + " actual=" + actual);
        }
    }

    private void dumpWindow(Program program, DecompInterface decompiler, Window window) throws Exception {
        Address start = program.getAddressFactory().getDefaultAddressSpace().getAddress(window.start);
        Address end = program.getAddressFactory().getDefaultAddressSpace().getAddress(window.end);
        println("");
        println("=== " + window.label + " " + start + ".." + end + " ===");

        disassemble(start);
        Function function = program.getFunctionManager().getFunctionContaining(start);
        if (function == null) {
            try {
                function = createFunction(start, window.label);
            } catch (Exception exc) {
                println("create_function_error=" + exc.getMessage());
            }
        }
        if (function == null) {
            println("function=<none>");
        } else {
            println("function=" + function.getName() + " entry=" + function.getEntryPoint());
            DecompileResults results = decompiler.decompileFunction(function, 30, monitor);
            println("decompile_completed=" + results.decompileCompleted());
            if (results.decompileCompleted() && results.getDecompiledFunction() != null) {
                println("--- decompiled_c ---");
                println(results.getDecompiledFunction().getC());
                println("--- end_decompiled_c ---");
            } else {
                println("decompile_error=" + results.getErrorMessage());
            }
        }

        println("--- disassembly_window ---");
        AddressSet set = new AddressSet(start, end);
        InstructionIterator instructions = program.getListing().getInstructions(set, true);
        while (instructions.hasNext()) {
            Instruction instruction = instructions.next();
            println(instruction.getAddress() + ": " + instruction.toString());
        }
        println("--- end_disassembly_window ---");
    }
}
