# How to get and install TimeIt

## Prerequisites

TimeIt is a Python/Tkinter application. All dependencies are Python standard library.  Before installing, ensure you have:

- Python 3.10 or later
- Tkinter (usually bundled with Python; on some Linux distributions it requires a separate package)

### Installing Tkinter on common Linux distributions
If it is not already as default in your Python3 installation.
```bash
# Debian / Ubuntu
sudo apt install python3-tk

# Fedora
sudo dnf install python3-tkinter

# Arch
sudo pacman -S tk
```

## Getting TimeIt

There are two ways to get a copy of TimeIt: downloading a zip archive of a release, or cloning the repository with git.


### From ZIP file
1. Go to the Releases page: https://github.com/pcardaba/TimeIt/releases
2. Find the version you want (the latest stable release is shown at the 
   top, marked Latest).
3. Under the **Assets** section of that release, click Source code (zip) to 
   download the archive, or Source code (tar.gz) if you prefer.
4. Extract the archive somewhere on your machine:
    - Linux / macOS: `unzip TimeIt-2.0.0.zip` (or use your file manager)
    - Windows: right-click the `.zip` → Extract All...
5. Rename extracted resulting directory from `TimeIt-2.0.0`  →  `TimeIt`  
6. Follow the instructions at [How to launch TimeIt](02_launch.md)

### From source (git clone)
If you have git installed and want to track updates:

```bash
git clone https://github.com/pcardaba/TimeIt.git
cd TimeIt
```
This gives you the latest state of the main branch. Optionally, to check out a specific release instead:

```bash
git checkout v2.0.0
```

No build step is required. The application runs directly from the cloned directory.


---

*Next: [How to launch TimeIt](02_launch.md)*
