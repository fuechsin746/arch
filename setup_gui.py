import subprocess, os

def run(cmd):
    subprocess.run(cmd, shell=True, check=True)

def menu():
    cmd = ('whiptail --title "GUI Setup" --menu "Choose Environment" 15 60 3 '
           '"1" "GNOME" "2" "KDE Plasma" "3" "Hyprland (UWSM + SDDM)" 3>&1 1>&2 2>&3')
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()

def configure_uwsm_hyprland():
    print("--> Configuring UWSM for Hyprland...")
    run("uwsm internal generate-entry hyprland")
    conf_path = os.path.expanduser("~/.config/hypr/hyprland.conf")
    os.makedirs(os.path.dirname(conf_path), exist_ok=True)
    settings = """
input {
    kb_layout = us
    touchpad {
        natural_scroll = yes
        tap-to-click = yes
    }
}
exec-once = uwsm app -- waybar
exec-once = uwsm app -- dunst
"""
    with open(conf_path, "a") as f: f.write(settings)

def sddm_hidpi():
    run("sudo mkdir -p /etc/sddm.conf.d")
    conf = '[General]\nEnableHiDPI=true\n'
    run(f"echo '{conf}' | sudo tee /etc/sddm.conf.d/hidpi.conf")

if __name__ == "__main__":
    choice = menu()
    # Install Yay
    run("git clone https://aur.archlinux.org/yay.git /tmp/yay && cd /tmp/yay && makepkg -si --noconfirm")
    
    utils = "xf86-input-libinput brightnessctl bluez bluez-utils power-profiles-daemon upower"
    apps = "firefox discord visual-studio-code-bin vlc pipewire-pulse gvfs-ntfs ntfs-3g ttf-cascadia-code"
    
    envs = {
        "1": "gnome gnome-extra gdm",
        "2": "plasma kde-applications sddm",
        "3": "hyprland uwsm sddm waybar kitty rofi-wayland xdg-desktop-portal-hyprland"
    }
    
    run(f"yay -S --noconfirm {envs.get(choice)} {utils} {apps}")
    run("sudo systemctl enable bluetooth power-profiles-daemon")
    
    if choice == "1": run("sudo systemctl enable gdm")
    else:
        sddm_hidpi()
        run("sudo systemctl enable sddm")
        if choice == "3": configure_uwsm_hyprland()

    print("\nSetup Complete. Reboot to enter your desktop!")
