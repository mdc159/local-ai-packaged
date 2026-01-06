#!/usr/bin/env python3
"""
start_services.py

This script starts the Supabase stack first, waits for it to initialize, and then starts
the local AI stack. Both stacks use the same Docker Compose project name ("localai")
so they appear together in Docker Desktop.
"""

import os
import subprocess
import shutil
import time
import argparse
import platform
import sys
import urllib.request
import urllib.error
import json

def run_command(cmd, cwd=None):
    """Run a shell command and print it."""
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)

def clone_supabase_repo():
    """Clone the Supabase repository using sparse checkout if not already present."""
    if not os.path.exists("supabase"):
        print("Cloning the Supabase repository...")
        # Check if git is available
        git_available = shutil.which("git") is not None
        if not git_available:
            print("Warning: Git is not available. Cannot clone Supabase repository.")
            print("Please install Git or ensure the supabase directory exists.")
            return
        run_command([
            "git", "clone", "--filter=blob:none", "--no-checkout",
            "https://github.com/supabase/supabase.git"
        ])
        os.chdir("supabase")
        run_command(["git", "sparse-checkout", "init", "--cone"])
        run_command(["git", "sparse-checkout", "set", "docker"])
        run_command(["git", "checkout", "master"])
        os.chdir("..")
    else:
        print("Supabase repository already exists, updating...")
        # Check if git is available
        git_available = shutil.which("git") is not None
        if git_available:
            try:
                original_dir = os.getcwd()
                os.chdir("supabase")
                run_command(["git", "pull"])
                os.chdir(original_dir)
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("Warning: Could not update Supabase repository. Using existing version.")
                if os.path.basename(os.getcwd()) == "supabase":
                    os.chdir("..")
        else:
            print("Warning: Git is not available. Using existing Supabase repository.")

def prepare_supabase_env():
    """Copy .env to .env in supabase/docker."""
    env_path = os.path.join("supabase", "docker", ".env")
    env_example_path = os.path.join(".env")
    print("Copying .env in root to .env in supabase/docker...")
    shutil.copyfile(env_example_path, env_path)

def stop_existing_containers(profile=None):
    print("Stopping and removing existing containers for the unified project 'localai'...")
    cmd = ["docker", "compose", "-p", "localai"]
    if profile and profile != "none":
        cmd.extend(["--profile", profile])
    cmd.extend(["-f", "docker-compose.yml", "down"])
    run_command(cmd)

def check_container_health(container_name_pattern="supabase", compose_file=None):
    """Check if containers are running and healthy."""
    containers = {}
    try:
        # Prefer docker compose ps if we have a compose file (more reliable for compose projects)
        if compose_file and os.path.exists(compose_file):
            # Run from project root (where start_services.py is located)
            # Use absolute path for compose file to avoid cwd issues
            abs_compose_file = os.path.abspath(compose_file) if not os.path.isabs(compose_file) else compose_file
            cmd = ["docker", "compose", "-p", "localai", "-f", abs_compose_file, "ps", "-a", "--format", "json"]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            if result.returncode == 0 and result.stdout.strip():
                # Parse JSON output from docker compose ps
                for line in result.stdout.strip().split('\n'):
                    if line:
                        try:
                            container_info = json.loads(line)
                            name = container_info.get("Name", "")
                            if container_name_pattern.lower() in name.lower():
                                status = container_info.get("State", "unknown")
                                health = container_info.get("Health", "N/A")
                                containers[name] = {"status": status, "health": health}
                        except json.JSONDecodeError:
                            continue
        
        # Fallback to docker ps if compose approach didn't work or wasn't available
        if not containers:
            # List all containers and filter by pattern
            cmd = ["docker", "ps", "-a", "--format", "{{.Names}}|{{.Status}}|{{.Health}}"]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            if result.returncode == 0 and result.stdout.strip():
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = line.split('|')
                        if len(parts) >= 2:
                            name = parts[0]
                            # Only include containers matching the pattern
                            if container_name_pattern.lower() in name.lower():
                                status = parts[1]
                                health = parts[2] if len(parts) > 2 else "N/A"
                                containers[name] = {"status": status, "health": health}
    except Exception:
        pass
    return containers

def start_supabase(environment=None):
    """Start the Supabase services (using its compose file)."""
    print("Starting Supabase services...")
    cmd = ["docker", "compose", "-p", "localai", "-f", "supabase/docker/docker-compose.yml"]
    if environment and environment == "public":
        cmd.extend(["-f", "docker-compose.override.public.supabase.yml"])
    cmd.extend(["up", "-d"])
    run_command(cmd)
    # Check container status immediately after startup
    time.sleep(2)  # Brief wait for containers to register
    compose_file = "supabase/docker/docker-compose.yml"
    containers_before = check_container_health("supabase", compose_file=compose_file)
    return containers_before

def start_supabase_with_retry(environment=None, max_retries=3):
    """Start Supabase services with retry logic for transient failures."""
    for attempt in range(1, max_retries + 1):
        try:
            print(f"Starting Supabase services (attempt {attempt}/{max_retries})...")
            containers = start_supabase(environment)
            
            # Wait a bit for containers to initialize before checking
            time.sleep(5)
            
            # Check for critical container failures
            compose_file = "supabase/docker/docker-compose.yml"
            containers_after_check = check_container_health("supabase", compose_file=compose_file)
            
            critical_failed = []
            for name, info in containers_after_check.items():
                if "supabase-db" in name or ("db" in name.lower() and "supabase" in name.lower()):
                    status_lower = info.get("status", "").lower()
                    health_lower = info.get("health", "").lower()
                    if "exited" in status_lower or "stopped" in status_lower or "unhealthy" in health_lower:
                        critical_failed.append(f"{name} ({info.get('status')} / {info.get('health')})")
            
            if critical_failed:
                if attempt < max_retries:
                    print(f"Critical containers failed: {', '.join(critical_failed)}")
                    print("Retrying in 15 seconds...")
                    time.sleep(15)
                    continue
                else:
                    print(f"ERROR: Critical containers failed after {max_retries} attempts: {', '.join(critical_failed)}")
                    print("Check 'docker compose -p localai -f supabase/docker/docker-compose.yml logs supabase-db' for details")
                    raise subprocess.CalledProcessError(1, "docker compose", "Critical containers failed")
            
            print("Successfully started Supabase services")
            return True
        except subprocess.CalledProcessError as e:
            if attempt < max_retries:
                print("Startup failed (likely transient issue), retrying in 15 seconds...")
                time.sleep(15)
            else:
                print(f"Failed to start Supabase services after {max_retries} attempts")
                print("Check 'docker compose -p localai -f supabase/docker/docker-compose.yml logs' for details")
                raise
    return False

def start_local_ai(profile=None, environment=None):
    """Start the local AI services (using its compose file)."""
    print("Starting local AI services...")
    cmd = ["docker", "compose", "-p", "localai"]
    if profile and profile != "none":
        cmd.extend(["--profile", profile])
    cmd.extend(["-f", "docker-compose.yml"])
    if environment and environment == "private":
        cmd.extend(["-f", "docker-compose.override.private.yml"])
    if environment and environment == "public":
        cmd.extend(["-f", "docker-compose.override.public.yml"])
    cmd.extend(["up", "-d"])
    run_command(cmd)

def start_local_ai_with_retry(profile=None, environment=None, max_retries=3):
    """Start local AI services with retry logic for transient health check failures."""
    for attempt in range(1, max_retries + 1):
        try:
            print(f"Starting local AI services (attempt {attempt}/{max_retries})...")
            start_local_ai(profile, environment)
            print("Successfully started all AI services")
            return True
        except subprocess.CalledProcessError:
            if attempt < max_retries:
                print("Startup failed (likely transient health check issue), retrying in 15 seconds...")
                time.sleep(15)
            else:
                print(f"Failed to start AI services after {max_retries} attempts")
                print("Check 'docker compose -p localai logs' for details")
                raise
    return False

def wait_for_supabase_health(max_wait_seconds=180, check_interval=10):
    """
    Wait for Supabase services to be healthy by polling the Kong API gateway and checking critical containers.

    Supabase services (analytics, pooler, etc.) can take 50-100+ seconds to initialize.
    This replaces the fixed 20-second sleep with active health checking.

    Args:
        max_wait_seconds: Maximum time to wait (default 180s = 3 minutes)
        check_interval: Seconds between health checks

    Returns:
        bool: True if healthy, False if timeout
    """
    print(f"Waiting for Supabase to be healthy (max {max_wait_seconds}s)...")
    start_time = time.time()
    attempt = 0
    critical_containers = ["supabase-db", "supabase-kong"]

    while time.time() - start_time < max_wait_seconds:
        attempt += 1
        elapsed = int(time.time() - start_time)

        # Check critical container health
        compose_file = "supabase/docker/docker-compose.yml"
        containers = check_container_health("supabase", compose_file=compose_file)
        
        db_healthy = False
        db_found = False
        for name, info in containers.items():
            if "supabase-db" in name or "db" in name.lower():
                db_found = True
                status_lower = info.get("status", "").lower()
                health_lower = info.get("health", "").lower()
                
                # Check if container is running and healthy
                if "running" in status_lower or "up" in status_lower:
                    if "healthy" in health_lower or health_lower == "n/a" or not health_lower:
                        # Container is running and either healthy or health check not configured
                        db_healthy = True
                    elif "unhealthy" in health_lower:
                        print(f"  WARNING: supabase-db container is unhealthy: {info.get('status')} / {info.get('health')}")
                elif "exited" in status_lower or "stopped" in status_lower:
                    print(f"  WARNING: supabase-db container has exited: {info.get('status')}")
        
        # If we can't find the DB container, don't block on it (graceful degradation)
        if not db_found and len(containers) == 0:
            db_healthy = True  # Assume OK if we can't check

        try:
            # Check Kong API gateway - any response means Supabase is up
            req = urllib.request.Request("http://localhost:8000/", method='HEAD')
            req.add_header('User-Agent', 'health-check')
            with urllib.request.urlopen(req, timeout=5) as resp:
                if db_healthy:
                    print(f"Supabase healthy after {elapsed}s (HTTP {resp.getcode()}, DB healthy)")
                    return True
                else:
                    print(f"  Attempt {attempt}: Kong responding but DB not healthy yet ({elapsed}s elapsed)")
        except urllib.error.HTTPError as e:
            # HTTP errors (401, 403, 404) still mean the service is running
            if e.code in [401, 403, 404, 406]:
                if db_healthy:
                    print(f"Supabase healthy after {elapsed}s (HTTP {e.code} - service responding, DB healthy)")
                    return True
                else:
                    print(f"  Attempt {attempt}: Kong responding but DB not healthy yet ({elapsed}s elapsed)")
            else:
                print(f"  Attempt {attempt}: HTTP {e.code} ({elapsed}s elapsed)")
        except urllib.error.URLError as e:
            print(f"  Attempt {attempt}: Not ready - {e.reason} ({elapsed}s elapsed)")
        except Exception as e:
            print(f"  Attempt {attempt}: Error - {e} ({elapsed}s elapsed)")

        # Wait before next check
        remaining = max_wait_seconds - (time.time() - start_time)
        if remaining > check_interval:
            time.sleep(check_interval)
        elif remaining > 0:
            time.sleep(remaining)

    print(f"WARNING: Supabase health check timed out after {max_wait_seconds}s")
    print("Proceeding with AI services startup anyway...")
    return False

def generate_searxng_secret_key():
    """Generate a secret key for SearXNG based on the current platform."""
    print("Checking SearXNG settings...")
    
    # Define paths for SearXNG settings files
    settings_path = os.path.join("searxng", "settings.yml")
    settings_base_path = os.path.join("searxng", "settings-base.yml")
    
    # Check if settings-base.yml exists
    if not os.path.exists(settings_base_path):
        print(f"Warning: SearXNG base settings file not found at {settings_base_path}")
        return
    
    # Check if settings.yml exists, if not create it from settings-base.yml
    if not os.path.exists(settings_path):
        print(f"SearXNG settings.yml not found. Creating from {settings_base_path}...")
        try:
            shutil.copyfile(settings_base_path, settings_path)
            print(f"Created {settings_path} from {settings_base_path}")
        except Exception as e:
            print(f"Error creating settings.yml: {e}")
            return
    else:
        print(f"SearXNG settings.yml already exists at {settings_path}")
    
    print("Generating SearXNG secret key...")
    
    # Detect the platform and run the appropriate command
    system = platform.system()
    
    try:
        if system == "Windows":
            print("Detected Windows platform, using PowerShell to generate secret key...")
            # PowerShell command to generate a random key and replace in the settings file
            ps_command = [
                "powershell", "-Command",
                "$randomBytes = New-Object byte[] 32; " +
                "(New-Object Security.Cryptography.RNGCryptoServiceProvider).GetBytes($randomBytes); " +
                "$secretKey = -join ($randomBytes | ForEach-Object { \"{0:x2}\" -f $_ }); " +
                "(Get-Content searxng/settings.yml) -replace 'ultrasecretkey', $secretKey | Set-Content searxng/settings.yml"
            ]
            subprocess.run(ps_command, check=True)
            
        elif system == "Darwin":  # macOS
            print("Detected macOS platform, using sed command with empty string parameter...")
            # macOS sed command requires an empty string for the -i parameter
            openssl_cmd = ["openssl", "rand", "-hex", "32"]
            random_key = subprocess.check_output(openssl_cmd).decode('utf-8').strip()
            sed_cmd = ["sed", "-i", "", f"s|ultrasecretkey|{random_key}|g", settings_path]
            subprocess.run(sed_cmd, check=True)
            
        else:  # Linux and other Unix-like systems
            print("Detected Linux/Unix platform, using standard sed command...")
            # Standard sed command for Linux
            openssl_cmd = ["openssl", "rand", "-hex", "32"]
            random_key = subprocess.check_output(openssl_cmd).decode('utf-8').strip()
            sed_cmd = ["sed", "-i", f"s|ultrasecretkey|{random_key}|g", settings_path]
            subprocess.run(sed_cmd, check=True)
            
        print("SearXNG secret key generated successfully.")
        
    except Exception as e:
        print(f"Error generating SearXNG secret key: {e}")
        print("You may need to manually generate the secret key using the commands:")
        print("  - Linux: sed -i \"s|ultrasecretkey|$(openssl rand -hex 32)|g\" searxng/settings.yml")
        print("  - macOS: sed -i '' \"s|ultrasecretkey|$(openssl rand -hex 32)|g\" searxng/settings.yml")
        print("  - Windows (PowerShell):")
        print("    $randomBytes = New-Object byte[] 32")
        print("    (New-Object Security.Cryptography.RNGCryptoServiceProvider).GetBytes($randomBytes)")
        print("    $secretKey = -join ($randomBytes | ForEach-Object { \"{0:x2}\" -f $_ })")
        print("    (Get-Content searxng/settings.yml) -replace 'ultrasecretkey', $secretKey | Set-Content searxng/settings.yml")

def check_and_fix_docker_compose_for_searxng():
    """Check and modify docker-compose.yml for SearXNG first run."""
    docker_compose_path = "docker-compose.yml"
    if not os.path.exists(docker_compose_path):
        print(f"Warning: Docker Compose file not found at {docker_compose_path}")
        return
    
    try:
        # Read the docker-compose.yml file
        with open(docker_compose_path, 'r') as file:
            content = file.read()
        
        # Default to first run
        is_first_run = True
        
        # Check if Docker is running and if the SearXNG container exists
        try:
            # Check if the SearXNG container is running
            container_check = subprocess.run(
                ["docker", "ps", "--filter", "name=searxng", "--format", "{{.Names}}"],
                capture_output=True, text=True, check=True
            )
            searxng_containers = container_check.stdout.strip().split('\n')
            
            # If SearXNG container is running, check inside for uwsgi.ini
            if any(container for container in searxng_containers if container):
                container_name = next(container for container in searxng_containers if container)
                print(f"Found running SearXNG container: {container_name}")
                
                # Check if uwsgi.ini exists inside the container
                container_check = subprocess.run(
                    ["docker", "exec", container_name, "sh", "-c", "[ -f /etc/searxng/uwsgi.ini ] && echo 'found' || echo 'not_found'"],
                    capture_output=True, text=True, check=False
                )
                
                if "found" in container_check.stdout:
                    print("Found uwsgi.ini inside the SearXNG container - not first run")
                    is_first_run = False
                else:
                    print("uwsgi.ini not found inside the SearXNG container - first run")
                    is_first_run = True
            else:
                print("No running SearXNG container found - assuming first run")
        except Exception as e:
            print(f"Error checking Docker container: {e} - assuming first run")
        
        if is_first_run and "cap_drop: - ALL" in content:
            print("First run detected for SearXNG. Temporarily removing 'cap_drop: - ALL' directive...")
            # Temporarily comment out the cap_drop line
            modified_content = content.replace("cap_drop: - ALL", "# cap_drop: - ALL  # Temporarily commented out for first run")
            
            # Write the modified content back
            with open(docker_compose_path, 'w') as file:
                file.write(modified_content)
                
            print("Note: After the first run completes successfully, you should re-add 'cap_drop: - ALL' to docker-compose.yml for security reasons.")
        elif not is_first_run and "# cap_drop: - ALL  # Temporarily commented out for first run" in content:
            print("SearXNG has been initialized. Re-enabling 'cap_drop: - ALL' directive for security...")
            # Uncomment the cap_drop line
            modified_content = content.replace("# cap_drop: - ALL  # Temporarily commented out for first run", "cap_drop: - ALL")
            
            # Write the modified content back
            with open(docker_compose_path, 'w') as file:
                file.write(modified_content)
    
    except Exception as e:
        print(f"Error checking/modifying docker-compose.yml for SearXNG: {e}")

def main():
    parser = argparse.ArgumentParser(description='Start the local AI and Supabase services.')
    parser.add_argument('--profile', choices=['cpu', 'gpu-nvidia', 'gpu-amd', 'none'], default='cpu',
                      help='Profile to use for Docker Compose (default: cpu)')
    parser.add_argument('--environment', choices=['private', 'public'], default='private',
                      help='Environment to use for Docker Compose (default: private)')
    args = parser.parse_args()

    clone_supabase_repo()
    prepare_supabase_env()
    
    # Generate SearXNG secret key and check docker-compose.yml
    generate_searxng_secret_key()
    check_and_fix_docker_compose_for_searxng()
    
    stop_existing_containers(args.profile)

    # Start Supabase first with retry logic
    start_supabase_with_retry(args.environment, max_retries=3)

    # Wait for Supabase to be healthy (replaces fixed 20s sleep)
    wait_for_supabase_health(max_wait_seconds=180, check_interval=10)

    # Then start the local AI services with retry logic
    start_local_ai_with_retry(args.profile, args.environment, max_retries=3)

if __name__ == "__main__":
    main()
