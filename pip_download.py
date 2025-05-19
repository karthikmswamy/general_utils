"""Script to download packages from requirements.txt
skipping libraries that cannot be found"""
import subprocess


def download_package(install_package, download_dir, platform=None, python_version=None, abi=None):
    """Download a package using pip.

    Args:
        install_package (str): The name of the package to install.
        download_dir (str): The directory to download the package to.
        platform (str, optional): The target platform for the package. Defaults to None.
        python_version (str, optional): The target Python version for the package. Defaults to None.
        abi (str, optional): The target ABI for the package. Defaults to None.
    """
    command = [
        "pip", "download", install_package,
        "-d", download_dir
    ]
    if platform:
        command.extend(["--platform", platform])
    if python_version:
        command.extend(["--python-version", python_version])
    if abi:
        command.extend(["--abi", abi])

    process = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True
    )
    if process.returncode == 0:
        print(f"Successfully downloaded: {install_package}")
    else:
        if "No matching distribution found" in process.stderr:
            print(f"Skipping {install_package}: No matching distribution found.")
        else:
            print(f"Error downloading {install_package}: {process.stderr}")

if __name__ == "__main__":
    REQUIREMENTS_FILE = "requirements.txt"
    DOWNLOAD_DIR = "vendor_wheels"
    TARGET_PLATFORM = "manylinux2014_x86_64"
    TARGET_PY_VER = "3.11"
    TARGET_ABI = "cp311"

    with open(REQUIREMENTS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            package = line.strip()
            if package and not package.startswith("#"):
                download_package(
                    package,
                    DOWNLOAD_DIR,
                    TARGET_PLATFORM,
                    TARGET_PY_VER,
                    TARGET_ABI
                )

    print("Finished processing requirements.")
