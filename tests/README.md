# Tests

## DMAX Optimization Tests

### `test_fast_dmax_extraction.py`
Integration test for the full DMAX optimization workflow with early subprocess termination.

**What it tests:**
- Complete workflow from CIF to optimized DMAX values
- Non-blocking subprocess execution
- Real-time .prn file monitoring
- Early termination once data is extracted
- File organization and output validation

**Usage:**
```bash
python tests/test_fast_dmax_extraction.py
```

**Configuration:**
Update `KSTR_EXECUTABLE` path at the top of the file to point to your KSTR executable.

---

### `test_prn_monitoring.py`
Unit test for the `.prn` file monitoring function that detects when the IQ=1 section is complete.

**What it tests:**
- Detection of .prn file existence
- Parsing of IQ=1 section
- Validation of data completeness

**Usage:**
```bash
python tests/test_prn_monitoring.py
```

No configuration needed - uses existing test files.

---

### `test_dmax_workflow.py`
Example script demonstrating the DMAX optimization workflow.

**What it shows:**
- How to set up DMAX optimization parameters
- Expected output and logging
- Integration with existing workflows

**Usage:**
```bash
python tests/test_dmax_workflow.py
```

**Configuration:**
Update `KSTR_EXECUTABLE` path and adjust parameters as needed.

---

## Running Tests

All tests can be run independently:

```bash
# Run integration test
cd /path/to/EMTO_input_automation
python tests/test_fast_dmax_extraction.py

# Run unit test
python tests/test_prn_monitoring.py

# Run example workflow
python tests/test_dmax_workflow.py
```

## Requirements

- KSTR executable (for integration tests)
- Valid CIF files (included in `testing/` directory)
- Python 3.7+ with required dependencies

## Expected Output

### Successful Run
```
✓ Created 3 KSTR input files
Running KSTR for c/a = 1.02... ✓ (data extracted in 0.0s)
Running KSTR for c/a = 1.00... ✓ (data extracted in 0.0s)
Running KSTR for c/a = 0.98... ✓ (data extracted in 0.0s)

DMAX OPTIMIZATION COMPLETE
```

### Failed Run
Common issues and solutions are documented in [DMAX_OPTIMIZATION.md](../DMAX_OPTIMIZATION.md#troubleshooting).
