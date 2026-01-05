# CSI Replicator GUI

A Python-based GUI tool to replicate Docker images between Harbor registries (e.g., from multiple projects to various site-specific registries) using `skopeo`.this developed for instances where you have access to replicate through skopeo but no direct access authentication to foreighn harbors. 

## Features
- 🖥️ **User Friendly GUI**: Select environments and input tags easily.
- 🚀 **Multi-Environment Support**: Replicate to multiple destinations simultaneously.
- 🔍 **Smart Source Detection**: Automatically checks multiple projects to find the source image.
- 🔒 **Secure**: Configuration and credentials are loaded from environment variables.

## Prerequisites
- **Python 3.9+**
- **System Tools**:
  - `skopeo`: For image inspection and copying.
  - `pv` (Pipe Viewer): For progress bars.
  - `tkinter`: Standard Python GUI library (usually included or via `sudo apt install python3-tk`).

## Setup

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd csi-replicator
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**:
   Copy the example configuration:
   ```bash
   cp .env.example .env
   ```
   
   Open `.env` and configure your registries:
   - `SOURCE_REGISTRY`: The hostname of your source registry.
   - `SOURCE_PROJECTS`: Comma-separated list of projects to search in.
   - `ENV_{N}`: Connection strings for destination environments.
     Format: `HOSTNAME:PROJECT:REPO:USERNAME:PASSWORD`

## Usage

1. **Start the application**:
   ```bash
   python3 replicator_gui.py
   ```

2. **Replicate**:
   - Enter your **Source Registry Credentials**.
   - Enter the **Image Tag** (e.g., `my-app:v1.0`).
   - Select the target environments.
   - Click **Start Replication**.

## Security Note
- Credentials in `.env` are excluded from git via `.gitignore`.
- Ensure you do not commit your `.env` file.

## License
MIT
