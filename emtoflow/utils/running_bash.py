import subprocess
import sys
import os



def run_sbatch(script, path):
    """
    Submits the script to SLURM:
        sbatch run_Co.sh
    """
    print("Submitting script with sbatch...")
    result = subprocess.run(
        ["sbatch", script], cwd=path,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print("SBATCH submission failed:")
        print(result.stderr)
        sys.exit(1)
    else:
        print("SBATCH submission successful:")
        print(result.stdout)


def chmod_and_run(script, path, stdout_file="output.log", stderr_file="error.log"):
    """
    Makes the script executable and runs it.
    stdout_file: file to save standard output
    stderr_file: file to save error messages
    """
    stdout_file = os.path.join(path, stdout_file)
    stderr_file = os.path.join(path, stderr_file)

    print("Making script executable and running...")
    subprocess.run(["chmod", "+x", script], check=True, cwd=path)

    result = subprocess.run(["./" + script], capture_output=True, text=True, cwd=path)

    if result.returncode != 0:
        print("Running failed")
        with open(stderr_file, "w") as f:
            f.write(result.stderr)
        sys.exit(1)
    else:
        print("Running finished successfully")
        with open(stdout_file, "w") as f:
            f.write(result.stdout)

