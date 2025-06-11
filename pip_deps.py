import subprocess
import os
import sys
import shutil
import json

def get_base_package_name(package_line):
    """Extracts the base package name (e.g., 'numpy' from 'numpy==1.23.4')"""
    # Split by any version specifier (==, >=, <=, >, <, !=, ~)
    base_name = package_line.strip().split("==")[0].split(">=")[0].split("<=")[0].split(">")[0].split("<")[0].split("!=")[0].split("~=")[0].strip()
    return base_name.lower() # Normalize to lowercase for consistent comparison

def split_requirements(original_req_file, independent_req_file, dependent_req_file):
    temp_venv_dir = "temp_pip_env_for_analysis"

    # 1. Read original requirements.txt
    original_packages_raw = []
    try:
        with open(original_req_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    original_packages_raw.append(line)
        if not original_packages_raw:
            print(f"Warning: {original_req_file} is empty or contains only comments.")
            return
    except FileNotFoundError:
        print(f"Error: {original_req_file} not found.")
        return

    original_packages_normalized = {get_base_package_name(p) for p in original_packages_raw}

    print(f"Analyzing {len(original_packages_raw)} packages from {original_req_file}...")

    try:
        # 2. Create a temporary virtual environment
        print(f"Creating temporary virtual environment: {temp_venv_dir}")
        subprocess.run([sys.executable, "-m", "venv", temp_venv_dir], check=True, capture_output=True)

        # Determine the pip executable path within the venv
        if sys.platform == "win32":
            pip_executable = os.path.join(temp_venv_dir, "Scripts", "pip.exe")
        else:
            pip_executable = os.path.join(temp_venv_dir, "bin", "pip")

        # 3. Install pipdeptree into the venv
        print("Installing pipdeptree into temporary environment...")
        subprocess.run([pip_executable, "install", "pipdeptree"], check=True, capture_output=True)

        # 4. Install all packages from requirements.txt into the venv
        print("Installing all requirements into temporary environment for dependency analysis. This may take a while...")
        # Use --no-deps to avoid installing transitive dependencies if already listed, but pipdeptree works better with them installed.
        # However, for 700+ libraries, installing all may be very slow.
        # Let's try to install directly from the requirements.txt, which will handle dependencies.
        # We also need to specify --prefer-binary for faster installs, but still allow source for others.
        try:
            subprocess.run([pip_executable, "install", "-r", original_req_file], check=True, capture_output=True, text=True)
            print("All requirements installed in temporary environment.")
        except subprocess.CalledProcessError as e:
            print(f"Error installing requirements into temporary environment. This might indicate issues with some packages or their dependencies. Error output:\n{e.stderr}")
            print("Attempting to proceed with partial installation data. Results might be inaccurate.")
            # If installation fails, pipdeptree might still give partial data, but it's less reliable.
            # We'll continue but warn the user.

        # 5. Generate dependency tree using pipdeptree --json
        print("Generating dependency tree...")
        result = subprocess.run([pip_executable, "list", "--format=json"], check=True, capture_output=True, text=True)
        installed_packages_list = json.loads(result.stdout)
        installed_package_names = {pkg['name'].lower() for pkg in installed_packages_list}


        # Instead of --json for pipdeptree, let's build the graph manually using pip show for more control and less reliance on full tree
        # This will be slower but might be more resilient if full pipdeptree is hard to parse for large list
        # For simplicity and robust parsing, we will use pipdeptree --json directly which is designed for this.
        # Re-attempting pipdeptree --json after installing all requirements.
        pipdeptree_result = subprocess.run([pip_executable, "deptree", "--json"], check=True, capture_output=True, text=True)
        dependency_tree = json.loads(pipdeptree_result.stdout)

        # 6. Parse the JSON output and identify depended-upon packages
        depended_upon_set = set()
        for pkg_info in dependency_tree:
            pkg_name = pkg_info['key'] # The package itself
            # Check if this package was originally in our requirements.txt
            if pkg_name in original_packages_normalized:
                for dep_info in pkg_info.get('dependencies', []):
                    dep_name = dep_info['key']
                    # If a dependency is also one of our original top-level requirements
                    if dep_name in original_packages_normalized:
                        depended_upon_set.add(dep_name)

        # 7. Categorize Packages
        independent_packages = []
        dependent_packages = []

        for original_line in original_packages_raw:
            base_name = get_base_package_name(original_line)
            if base_name in depended_upon_set:
                dependent_packages.append(original_line)
            else:
                independent_packages.append(original_line)

        # 8. Write to new requirements.txt files
        print(f"\nWriting to {independent_req_file} ({len(independent_packages)} packages)...")
        with open(independent_req_file, "w") as f:
            for pkg in independent_packages:
                f.write(pkg + "\n")

        print(f"Writing to {dependent_req_file} ({len(dependent_packages)} packages)...")
        with open(dependent_req_file, "w") as f:
            for pkg in dependent_packages:
                f.write(pkg + "\n")

        print("\nRequirements files split successfully!")

    except subprocess.CalledProcessError as e:
        print(f"An error occurred during subprocess execution: {e.cmd}")
        print(f"Return Code: {e.returncode}")
        print(f"STDOUT:\n{e.stdout}")
        print(f"STDERR:\n{e.stderr}")
        print("Please check the error messages and ensure 'pip' is working correctly.")
    except json.JSONDecodeError:
        print("Error: Could not parse JSON output from pipdeptree. This might indicate an issue with pipdeptree or an unusual output.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        # 9. Clean up the temporary virtual environment
        if os.path.exists(temp_venv_dir):
            print(f"Cleaning up temporary virtual environment: {temp_venv_dir}")
            try:
                shutil.rmtree(temp_venv_dir)
                print("Temporary environment removed.")
            except OSError as e:
                print(f"Error removing temporary directory {temp_venv_dir}: {e}")

if __name__ == "__main__":
    # Define your input and output file names
    original_requirements_file = "requirements.txt"
    independent_requirements_file = "requirements_independent.txt"
    dependent_requirements_file = "requirements_dependent.txt"

    split_requirements(original_requirements_file, independent_requirements_file, dependent_requirements_file)
