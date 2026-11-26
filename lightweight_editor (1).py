#!/usr/bin/env python3
"""Edit source code in Vim, install its runtime with Winget, and run it."""

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
CODE_DIR = SCRIPT_DIR / "Code"


def run_command(cmd, check=True, capture_output=False, interactive=False):
    kwargs = {"check": check}
    if capture_output:
        kwargs["capture_output"] = True
        kwargs["text"] = True
    if interactive:
        kwargs.pop("capture_output", None)
        kwargs.pop("text", None)
    return subprocess.run(cmd, shell=False, **kwargs)


def refresh_windows_path():
    if not sys.platform.startswith("win"):
        return
    machine = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command",
         "[Environment]::GetEnvironmentVariable('Path','Machine')"],
        capture_output=True, text=True, check=False,
    ).stdout.strip()
    user = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command",
         "[Environment]::GetEnvironmentVariable('Path','User')"],
        capture_output=True, text=True, check=False,
    ).stdout.strip()
    os.environ["PATH"] = ";".join(part for part in (machine, user, os.environ.get("PATH", "")) if part)


def is_tool(name):
    refresh_windows_path()
    return shutil.which(name) is not None


def install_winget(package_id):
    if not sys.platform.startswith("win"):
        raise RuntimeError("Automatic runtime installation is implemented with Winget on Windows.")
    if not shutil.which("winget"):
        raise RuntimeError("Winget is not available. Install it, or install the runtime manually.")
    print(f"Installing {package_id} through Winget...")
    run_command([
        "winget", "install", "-e", "--id", package_id,
        "--accept-package-agreements", "--accept-source-agreements",
    ])
    refresh_windows_path()


def ensure_vim():
    for editor in ("vim", "nvim", "gvim"):
        if is_tool(editor):
            return editor
    local_vim = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Vim" / "vim.exe"
    if local_vim.is_file():
        return str(local_vim)
    install_winget("vim.vim")
    for editor in ("vim", "nvim", "gvim"):
        if is_tool(editor):
            return editor
    raise RuntimeError("Vim was installed but is not on PATH. Restart the terminal and try again.")


LANGUAGE_CONFIG = {
    ".c": ("C", ("gcc", "clang"), "MartinStorsjo.LLVM-MinGW.UCRT"),
    ".cpp": ("C++", ("g++", "clang++"), "MartinStorsjo.LLVM-MinGW.UCRT"),
    ".cc": ("C++", ("g++", "clang++"), "MartinStorsjo.LLVM-MinGW.UCRT"),
    ".cxx": ("C++", ("g++", "clang++"), "MartinStorsjo.LLVM-MinGW.UCRT"),
    ".java": ("Java", ("javac", "java"), "EclipseAdoptium.Temurin.21.JDK"),
    ".py": ("Python", ("python", "python3"), "Python.Python.3.13"),
    ".js": ("JavaScript", ("node",), "OpenJS.NodeJS.LTS"),
    ".ts": ("TypeScript", ("node", "npx"), "OpenJS.NodeJS.LTS"),
    ".cs": ("C#", ("dotnet",), "Microsoft.DotNet.SDK.8"),
    ".go": ("Go", ("go",), "GoLang.Go"),
    ".rs": ("Rust", ("rustc", "cargo"), "Rustlang.Rustup"),
    ".rb": ("Ruby", ("ruby",), "RubyInstallerTeam.RubyWithDevKit"),
    ".php": ("PHP", ("php",), "PHP.PHP.8.4"),
    ".lua": ("Lua", ("lua",), "LuaForWindows.LuaForWindows"),
    ".pl": ("Perl", ("perl",), "Perl.Perl"),
    ".r": ("R", ("Rscript",), "RProject.R"),
    ".ps1": ("PowerShell", ("pwsh", "powershell"), "Microsoft.PowerShell"),
    ".sh": ("Shell", ("bash",), None),
    ".bat": ("Windows Batch", ("cmd",), None),
    ".cmd": ("Windows Batch", ("cmd",), None),
}


def ensure_tool(config):
    language, tools, winget_id = config
    for tool in tools:
        if is_tool(tool):
            return tool
    if winget_id is None:
        raise RuntimeError(f"Could not find a runtime for {language}. Install it manually.")
    print(f"{language} runtime not found.")
    install_winget(winget_id)
    if language == "Rust":
        run_command(["rustup", "default", "stable"], check=False)
        refresh_windows_path()
    if language == "TypeScript" and is_tool("npm"):
        run_command(["npm", "install", "-g", "tsx"], check=False)
        refresh_windows_path()
    for tool in tools:
        if is_tool(tool):
            return tool
    raise RuntimeError(
        f"{language} runtime was installed but {', '.join(tools)} is not on PATH. "
        "Restart the terminal and run the script again."
    )


def install_chedit_command():
    if not sys.platform.startswith("win"):
        raise RuntimeError("The chedit command launcher is currently supported on Windows.")
    launcher_dir = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WindowsApps"
    if not launcher_dir.is_dir():
        raise RuntimeError(f"Command folder does not exist: {launcher_dir}")
    launcher = launcher_dir / "chedit.cmd"
    script_path = str(Path(__file__).resolve())
    content = '@echo off\npy -3 "{}" %*\n'.format(script_path)
    if launcher.exists():
        existing = launcher.read_text(encoding="utf-8", errors="replace")
        existing_lines = [line for line in existing.splitlines() if line.strip()]
        expected_lines = [line for line in content.splitlines() if line.strip()]
        if existing_lines != expected_lines:
            raise RuntimeError(f"Not replacing existing command launcher: {launcher}")
        return launcher
    launcher.write_text(content, encoding="utf-8")
    return launcher


def print_process_output(result):
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="")


def run_language(source, language, primary_tool):
    src = source
    print(f"Detected language: {language}")
    print(f"Using runtime: {primary_tool}")
    print("--- Output ---")

    if language == "C":
        output = src.with_suffix(".exe" if sys.platform.startswith("win") else "")
        compile_cmd = [primary_tool, str(src), "-o", str(output)]
        result = run_command(compile_cmd, check=True, capture_output=True)
        print_process_output(result)
        return run_command([str(output)], check=True, capture_output=True)

    if language == "C++":
        output = src.with_suffix(".exe" if sys.platform.startswith("win") else "")
        compile_cmd = [primary_tool, str(src), "-o", str(output)]
        result = run_command(compile_cmd, check=True, capture_output=True)
        print_process_output(result)
        return run_command([str(output)], check=True, capture_output=True)

    if language == "Java":
        ensure_tool(LANGUAGE_CONFIG[".java"])
        build_dir = src.parent / ".java-build"
        build_dir.mkdir(parents=True, exist_ok=True)
        javac = shutil.which("javac")
        java = shutil.which("java")
        compile_result = run_command(
            [javac, "-d", str(build_dir), str(src)], check=True, capture_output=True
        )
        print_process_output(compile_result)
        text = src.read_text(encoding="utf-8", errors="replace")
        match = re.search(r"\b(?:public\s+)?class\s+([A-Za-z_$][\w$]*)", text)
        if not match:
            raise RuntimeError("Could not find a Java class to execute.")
        return run_command(
            [java, "-cp", str(build_dir), match.group(1)],
            check=True, capture_output=True,
        )

    if language == "Python":
        return run_command([primary_tool, str(src)], check=True, capture_output=True)
    if language == "JavaScript":
        return run_command([primary_tool, str(src)], check=True, capture_output=True)
    if language == "TypeScript":
        tsx = shutil.which("tsx")
        if tsx:
            return run_command([tsx, str(src)], check=True, capture_output=True)
        npx = shutil.which("npx")
        return run_command([npx, "--yes", "tsx", str(src)], check=True, capture_output=True)
    if language == "C#":
        project_dir = src.parent / ".dotnet-run"
        project_dir.mkdir(parents=True, exist_ok=True)
        project = project_dir / "Program.csproj"
        project.write_text(
            '<Project Sdk="Microsoft.NET.Sdk">'
            '<PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net8.0</TargetFramework>'
            f'<EnableDefaultCompileItems>false</EnableDefaultCompileItems></PropertyGroup>'
            f'<ItemGroup><Compile Include="{src.as_posix()}" /></ItemGroup></Project>',
            encoding="utf-8",
        )
        return run_command(
            [primary_tool, "run", "--project", str(project)],
            check=True, capture_output=True,
        )
    if language == "Go":
        return run_command([primary_tool, "run", str(src)], check=True, capture_output=True)
    if language == "Rust":
        output = src.with_suffix(".exe" if sys.platform.startswith("win") else "")
        run_command([primary_tool, str(src), "-o", str(output)], check=True, capture_output=True)
        return run_command([str(output)], check=True, capture_output=True)
    if language == "Ruby":
        return run_command([primary_tool, str(src)], check=True, capture_output=True)
    if language == "PHP":
        return run_command([primary_tool, str(src)], check=True, capture_output=True)
    if language == "Lua":
        return run_command([primary_tool, str(src)], check=True, capture_output=True)
    if language == "Perl":
        return run_command([primary_tool, str(src)], check=True, capture_output=True)
    if language == "R":
        return run_command([primary_tool, "--vanilla", str(src)], check=True, capture_output=True)
    if language == "PowerShell":
        return run_command([primary_tool, "-NoProfile", "-File", str(src)], check=True, capture_output=True)
    if language == "Shell":
        return run_command([primary_tool, str(src)], check=True, capture_output=True)
    if language == "Windows Batch":
        return run_command([primary_tool, "/d", "/s", "/c", f'call "{src}"'], check=True, capture_output=True)
    raise RuntimeError(f"No runner is configured for {language}.")


def main():
    parser = argparse.ArgumentParser(description="Edit, install, compile, and run source code.")
    parser.add_argument("file", nargs="?", help="Source file to create or edit in the Code folder")
    parser.add_argument("--no-edit", action="store_true", help="Compile/run without opening Vim")
    parser.add_argument(
        "--install-command", action="store_true",
        help="Install the Windows 'chedit' command launcher",
    )
    args = parser.parse_args()

    if args.install_command:
        try:
            print(f"Installed command: {install_chedit_command()}")
        except (OSError, RuntimeError) as error:
            print(f"Error installing command: {error}")
            sys.exit(1)
        return

    try:
        launcher = install_chedit_command()
        print(f"Command ready: chedit (launcher: {launcher})")
    except (OSError, RuntimeError) as error:
        print(f"Could not install chedit command automatically: {error}")
        print("Run this script with --install-command after fixing the issue.")

    if args.file:
        requested_path = Path(args.file).expanduser()
    else:
        requested_path = Path(input("Enter source filename: ")).expanduser()
    if requested_path.is_absolute():
        src = requested_path.resolve()
    else:
        src = (CODE_DIR / requested_path).resolve()
    CODE_DIR.mkdir(parents=True, exist_ok=True)
    src.parent.mkdir(parents=True, exist_ok=True)
    src.touch(exist_ok=True)

    config = LANGUAGE_CONFIG.get(src.suffix.lower())
    if config is None:
        print(
            f"Unsupported file extension '{src.suffix}'. "
            f"Supported extensions: {', '.join(LANGUAGE_CONFIG)}"
        )
        sys.exit(1)

    if not args.no_edit:
        editor = ensure_vim()
        print(f"Opening {editor} for {src}...")
        run_command([
            editor,
            "-c", "set laststatus=2",
            "-c", r"set statusline=F2:\ Save\ \|\ F10:\ Save\ and\ run\ \|\ i:\ Insert\ \|\ Esc:\ Normal\ \|\ :q!:\ Quit",
            "-c", "nnoremap <F2> :write<CR>",
            "-c", "inoremap <F2> <Esc>:write<CR>a",
            "-c", "nnoremap <F10> :write<CR>:quit<CR>",
            "-c", "inoremap <F10> <Esc>:write<CR>:quit<CR>",
            str(src),
        ], interactive=True)

    try:
        primary_tool = ensure_tool(config)
        result = run_language(src, config[0], primary_tool)
        print_process_output(result)
    except subprocess.CalledProcessError as error:
        print("Command failed:")
        print(error.stdout or "", end="")
        print(error.stderr or "", end="")
        sys.exit(error.returncode)
    except RuntimeError as error:
        print(f"Error: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
