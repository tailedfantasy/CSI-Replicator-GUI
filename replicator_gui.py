#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, scrolledtext
import subprocess
import threading
import re
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Harbor Source Projects to Check ---
SOURCE_REGISTRY = os.getenv("SOURCE_REGISTRY", "ENTER YOUR LOCAL HARBOR HERE")
SOURCE_PROJECTS = os.getenv("SOURCE_PROJECTS", "ENTER YOU PROJECT NAMES SEPERATED BY COMMA").split(",")
# --------------------------------------

# -----------------------------
# GUI setup
# -----------------------------
root = tk.Tk()
root.title("CSI Replicator GUI")
root.geometry("800x650") # Slightly taller to accommodate log area better

# Helper function for logging (defined early)
def log_message(message, color="black"):
    log_area.configure(state="normal")
    log_area.insert(tk.END, message + "\n", color)
    log_area.configure(state="disabled")
    log_area.see(tk.END)

# Input fields
tk.Label(root, text="Source Registry Username:").pack()
entry_user = tk.Entry(root, width=40)
entry_user.pack(pady=5)

tk.Label(root, text="Source Registry Password:").pack()
entry_pass = tk.Entry(root, width=40, show="*")
entry_pass.pack(pady=5)

tk.Label(root, text="Image(s) with tag (space-separated, e.g. repo:tag):").pack()
entry_tags = tk.Entry(root, width=60)
entry_tags.pack(pady=5)

# Environment selection
tk.Label(root, text="Select Environment(s):").pack()
envs_frame = tk.Frame(root)
envs_frame.pack(pady=5)

env_options = [
    "1) env name1", "2) env name2", "3) env name3", "4) env name4",
    "5) env name5", "6) env name6", "7) env name7", "8) env name8"
]
env_vars = []
for opt in env_options:
    var = tk.BooleanVar()
    cb = tk.Checkbutton(envs_frame, text=opt, variable=var)
    cb.pack(side="left", padx=5) # Changed to side="left" for better layout
    env_vars.append(var)

# Progress bar + label
progress_bar = ttk.Progressbar(root, orient="horizontal", length=600, mode="determinate")
progress_bar.pack(pady=10)

progress_label = tk.Label(root, text="Progress: 0%")
progress_label.pack()

# -----------------------------
# Start Replication button
# -----------------------------
def start_thread():
    threading.Thread(target=replicate, daemon=True).start()

btn_replicate = tk.Button(root, text="Start Replication", command=start_thread, bg="green", fg="white")
btn_replicate.pack(pady=10)

# Log output
log_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=100, height=20, state="disabled")
log_area.pack(pady=10)

# Tagging log colors
log_area.tag_configure("red", foreground="red")
log_area.tag_configure("green", foreground="green")
log_area.tag_configure("blue", foreground="blue")
log_area.tag_configure("yellow", foreground="orange")
log_area.tag_configure("purple", foreground="purple")

# -----------------------------
# Helper functions
# -----------------------------
def run_command(cmd, env=None):
    """Runs a command and yields output lines."""
    process = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        bufsize=1, universal_newlines=True, env=env
    )
    for line in process.stdout:
        yield line.strip()
    process.wait()
    return process.returncode

def is_image_available(full_image_path):
    """Uses skopeo inspect to check if an image exists. Returns True/False."""
    # Note: skopeo login must be performed successfully before calling this.
    cmd = f"skopeo inspect --tls-verify=false docker://{full_image_path}"
    
    # We run the inspect command silently and check the return code
    result = subprocess.run(
        cmd, shell=True, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE
    )
    return result.returncode == 0

def find_image_in_projects(repo, tag, user, passwd):
    """Checks project1, project2, project3 for the image."""
    log_message(f"Checking existence for {repo}:{tag} in {SOURCE_PROJECTS}...", "purple")
    
    # Perform a single login before checking all projects
    log_message(f"Logging into {SOURCE_REGISTRY} for inspection...", "yellow")
    login_cmd = f"skopeo login https://{SOURCE_REGISTRY} --username {user} --password {passwd}"
    for line in run_command(login_cmd):
        log_message(line, "green")
    
    for project in SOURCE_PROJECTS:
        full_path = f"https://{SOURCE_REGISTRY}/{project}/{repo}:{tag}"
        # Fixed path construction to include protocol if needed or just registry path
        # skopeo inspect takes docker://registry/project/repo:tag
        inspect_path = f"{SOURCE_REGISTRY}/{project}/{repo}:{tag}"
        log_message(f"  -> Trying {project}...", "blue")
        
        if is_image_available(inspect_path):
            log_message(f"  ✔ Image found in {project}.", "green")
            # Return the full path of the successful source
            return inspect_path
    
    return None # Return None if not found in any project


def copy_image_with_progress(src, dest):
    log_message(f"Running: {src} -> {dest}", "blue")

    # Wrap skopeo with pv to capture progress
    # NOTE: 'pv' utility must be installed on your system for progress bar
    cmd = f"skopeo copy --all --src-tls-verify=false --dest-tls-verify=false {src} {dest} | pv -brt"

    process = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        universal_newlines=True
    )

    for line in process.stdout:
        line = line.strip()
        if not line:
            continue

        # Detect pv lines like "200MiB 0:00:10 [20.0MiB/s]"
        match = re.search(r'(\d+\.?\d*)(MiB|GiB).*?\[(\d+\.?\d*)MiB/s\]', line)
        if match:
            transferred, unit, speed = match.groups()
            transferred_mb = float(transferred) * (1024 if unit == "GiB" else 1)

            # pv does not know total size → show only transferred + speed
            progress_bar["mode"] = "indeterminate"
            progress_bar.start(50)
            progress_label.config(
                text=f"Transferred: {transferred_mb:.1f}MB @ {float(speed):.2f} MB/s"
            )
            root.update_idletasks()
        else:
            log_message(line, "green")

    process.wait()
    progress_bar.stop()
    progress_label.config(text="Progress: Done ✅")

def replicate():
    log_message("Starting replication...", "blue")
    user = entry_user.get().strip()
    passwd = entry_pass.get().strip()
    tags = entry_tags.get().strip().split()

    selected_envs = [i + 1 for i, var in enumerate(env_vars) if var.get()]
    if not selected_envs:
        log_message("❌ No environments selected.", "red")
        return

    if not tags:
        log_message("❌ No tags specified.", "red")
        return

    DESTS = {}
    # Dynamically load configured environments ENV_1, ENV_2, etc.
    for i in range(1, 20): # Check for up to 20 environments
        env_config = os.getenv(f"ENV_{i}")
        if env_config:
            DESTS[i] = env_config

    # Warning if an environment is selected but not configured in .env
    for env_num in selected_envs:
        if env_num not in DESTS:
            log_message(f"❌ Env {env_num} is selected but 'ENV_{env_num}' is not set in .env file.", "red")
            return

    for tag_full in tags:
        try:
            repo, tag = tag_full.split(":", 1)
        except ValueError:
            log_message(f"❌ Invalid image format: {tag_full}. Must be 'repo:tag'. Skipping.", "red")
            continue

        log_message(f"\nProcessing {repo}:{tag}", "blue")

        # --- NEW: Find the source project where the image resides ---
        source_image_path = find_image_in_projects(repo, tag, user, passwd)

        if not source_image_path:
            log_message(f"❌ Image {repo}:{tag} not found in any source project ({', '.join(SOURCE_PROJECTS)}). Skipping replication.", "red")
            continue
        
        # Extract the source project from the full path
        match = re.search(r'[^/]+/(.+?)/[^/]+:\w+$', source_image_path)
        if match:
             src_repo = match.group(1)
        else:
            # Fallback (shouldn't happen if find_image_in_projects works)
            src_repo = "project1" # Default to project1 if extraction fails.


        # --- Proceed with replication using the found source path ---
        for env_num in selected_envs:
            if env_num not in DESTS:
                log_message(f"Env {env_num} not configured in script. Skipping.", "red")
                continue

            try:
                dest_registry, _, dest_repo, dest_user, dest_pass = DESTS[env_num].split(":")
            except ValueError:
                log_message(f"❌ Environment configuration for {env_num} is malformed. Skipping.", "red")
                continue
                
            log_message(f"Attempting replication from **{src_repo}** to Env {env_num}...", "yellow")
            
            # Login to destination
            log_message(f"Logging into {dest_registry}...", "yellow")
            login_cmd = f"skopeo login https://{dest_registry} --username {dest_user} --password {dest_pass}"
            for line in run_command(login_cmd):
                log_message(line, "green")

            # Source path is now dynamically set by find_image_in_projects
            src = f"docker://{source_image_path}"
            dest = f"docker://{dest_registry}/{dest_repo}/{repo}:{tag}"
            
            copy_image_with_progress(src, dest)

    log_message("\n✔ Replication finished.", "green")

root.mainloop()
