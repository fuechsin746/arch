💻 Modular Arch Linux Installer (Laptop Edition)

This repository contains a two-stage automated installation process for Arch Linux, optimized for AMD Laptops with NVMe storage, Btrfs snapshots, and a Hyprland desktop environment.
🏗️ Architecture Overview

The installation is split into two modules to ensure system stability and customizability:

    Stage 1: Base Install (base_install.py)

        Disk: Automatic NVMe detection and partitioning.

        Filesystem: Btrfs with subvolumes (@, @home, @log, @pkg, @snapshots).

        Drivers: AMDGPU, Multi-filesystem support (NTFS, XFS, F2FS), and Libinput for trackpads.

        Boot: GRUB with os-prober for dual-booting and grub-btrfs for snapshot booting.

    Stage 2: Desktop & AUR (setup_gui.py)

        TUI Menu: Choose between GNOME, KDE, or Hyprland.

        Wayland Stack: Hyprland managed via UWSM for robust session handling.

        Laptop Tweaks: SDDM HiDPI scaling, Tap-to-click, and Battery optimization (power-profiles-daemon).

        AUR: Automated installation of yay and common productivity apps.

🚀 Installation Instructions
1. Preparation

Boot into the Arch Linux Live ISO and connect to the internet:
Bash

iwctl
# Connect to your WiFi
ping google.com

2. Execute Base Installation

Download and run the first script to prepare the hardware:
Bash

curl -O https://raw.githubusercontent.com/your-username/your-repo/main/base_install.py
python base_install.py

Follow the TUI prompts for Hostname, Username, and Password.
3. First Reboot

Remove the USB drive and reboot into the new system. Log in with your user credentials.
4. Execute GUI Setup

Run the second script to install the desktop environment and apps:
Bash

curl -O https://raw.githubusercontent.com/your-username/your-repo/main/setup_gui.py
python setup_gui.py

Select Hyprland in the menu to trigger the UWSM/SDDM configuration.
🛡️ Recovery & Maintenance
Snapshot Rollback

If a system update or configuration change breaks your GUI:

    Reboot the laptop.

    In the GRUB Menu, select "Arch Linux snapshots".

    Select a snapshot from before the break.

    Once booted, run: snapper rollback to make the snapshot permanent.

Power Management

Use the following command to toggle battery modes on the fly:
Bash

powerprofilesctl set power-saver  # Best for battery
powerprofilesctl set performance   # Best for gaming/coding

⌨️ Hyprland Cheat Sheet

    Terminal: Super + Q

    Launcher: Super + R

    Kill App: Super + C

    Logout: Super + M

    Floating: Super + V
