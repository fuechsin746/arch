#!/usr/bin/env python3
import subprocess, os

def run(cmd):
    subprocess.run(cmd, shell=True, check=True)

def configure_xdg_apps(user):
    """Force common apps to respect XDG directories via environment and symlinks."""
    print("--> Optimizing App Directories (Discord, VS Code, etc.)...")
    
    config_home = f"/home/{user}/.config"
    data_home = f"/home/{user}/.local/share"
    
    # Pre-create directories
    os.makedirs(f"{config_home}/discord", exist_ok=True)
    os.makedirs(f"{data_home}/vscode/extensions", exist_ok=True)

    # Force VS Code to use XDG for extensions and data
    # We add this to the user's .zshrc created in the base script
    zshrc_path = f"{config_home}/zsh/.zshrc"
    xdg_exports = f"""
# XDG App Fixes
export VSCODE_PORTABLE="\\$XDG_DATA_HOME/vscode"
export ELECTRON_CONFIG_CACHE="\\$XDG_CONFIG_HOME/electron"
"""
    with open(zshrc_path, "a") as f:
        f.write(xdg_exports)

def configure_uwsm_hyprland(layout):
    print(f"--> Configuring UWSM & Hyprland ({layout})...")
    run("uwsm internal generate-entry hyprland")
    
    # Hyprland config is already in ~/.config by default
    conf_path = os.path.expanduser("~/.config/hypr/hyprland.conf")
    os.makedirs(os.path.dirname(conf_path), exist_ok=True)
    
    settings = f"""
input {{
    kb_layout = {layout}
    touchpad {{
        natural_scroll = yes
        tap-to-click = yes
    }}
}}

# Ensure environment variables are imported to the session
exec-once = uwsm app -- waybar
exec-once = uwsm app -- dunst
exec-once = uwsm app -- nm-applet
"""
    with open(conf_path, "a") as f:
        f.write(settings)

if __name__ == "__main__":
    print("=== ARCH LINUX GUI SETUP (XDG COMPLIANT) ===")
    print("1) GNOME\\n2) KDE Plasma\\n3) Hyprland (UWSM + SDDM)")
    choice = input("Select Environment [1-3]: ")

    # Detect user and layout
    user = os.getlogin() if os.getlogin() != "root" else os.environ.get("SUDO_USER", "user")
    layout = "us"
    if os.path.exists("/etc/vconsole.conf"):
        with open("/etc/vconsole.conf", "r") as f:
            for line in f:
                if "KEYMAP" in line: layout = line.split('=')[1].strip()

    # 1. Install Yay
    run("git clone https://aur.archlinux.org/yay.git /tmp/yay && cd /tmp/yay && makepkg -si --noconfirm")
    
    # 2. Package Lists
    utils = "xf86-input-libinput brightnessctl bluez bluez-utils power-profiles-daemon upower xdg-user-dirs"
    apps = "firefox discord visual-studio-code-bin vlc pipewire-pulse gvfs-ntfs ntfs-3g ttf-cascadia-code"
    
    envs = {
        "1": "gnome gnome-extra gdm",
        "2": "plasma kde-applications sddm",
        "3": "hyprland uwsm sddm waybar kitty rofi-wayland xdg-desktop-portal-hyprland"
    }
    
    # 3. Execution
    run(f"yay -S --noconfirm {envs.get(choice)} {utils} {apps}")
    run("sudo systemctl enable bluetooth power-profiles-daemon")
    
    # 4. App-Specific XDG Tweaks
    configure_xdg_apps(user)
    
    if choice == "3":
        configure_uwsm_hyprland(layout)
        run("sudo systemctl enable sddm")
    elif choice == "1":
        run("sudo systemctl enable gdm")
    else:
        run("sudo systemctl enable sddm")

    # Final touch: Update User Dirs (Documents, Downloads, etc.)
    run(f"sudo -u {user} xdg-user-dirs-update")
    
    run("rm -rf /tmp/yay")
    print(f"\\n[SUCCESS] GUI installed. {user}, please reboot!")
