import subprocess
import os

# --- Configuration ---
DISK = "/dev/nvme0n1"
HOSTNAME = "dell-dc15255"
USER = "bryanr"
TIMEZONE = "America/Chicago"
TEMP_PW = "temporary_password"

# Packages: Base + AMD Drivers + Zsh Plugins + Snapshot Tools
PACKAGES = [
    "base", "linux", "linux-firmware", "amd-ucode", "base-devel", 
    "git", "man-pages", "man-db", "texinfo", "pacman-contrib", 
    "nano", "vim", "xdg-user-dirs", "networkmanager", "wpa_supplicant", 
    "zsh", "zsh-autosuggestions", "zsh-syntax-highlighting", 
    "zram-generator", "grub", "efibootmgr", "snapper", "grub-btrfs", 
    "inotify-tools", "mesa", "xf86-video-amdgpu", "vulkan-radeon"
]

def run(cmd):
    print(f"--> Executing: {cmd}")
    subprocess.run(cmd, shell=True, check=True)

def setup_partitions():
    print("Partitioning and formatting NVMe drive...")
    # 1. Partitioning (GPT)
    run(f"sgdisk -Z {DISK}")
    run(f"sgdisk -n 1:0:+1G -t 1:ef00 {DISK}") # 1 GiB EFI
    run(f"sgdisk -n 2:0:+8G -t 2:8200 {DISK}") # 8 GiB Swap
    run(f"sgdisk -n 3:0:0 -t 3:8300 {DISK}")    # Rest Btrfs

    # 2. Filesystems
    run(f"mkfs.vfat -F32 {DISK}p1")
    run(f"mkswap {DISK}p2")
    run(f"mkfs.btrfs -f -L ARCH {DISK}p3")

    # 3. Create Btrfs Subvolumes
    run(f"mount {DISK}p3 /mnt")
    for sv in ["@", "@home", "@log", "@pkg", "@snapshots"]:
        run(f"btrfs subvolume create /mnt/{sv}")
    run("umount /mnt")

    # 4. Final Mounts with ZSTD Compression
    opts = "noatime,compress=zstd,commit=120"
    run(f"mount -o subvol=@,{opts} {DISK}p3 /mnt")
    
    for d in ["home", "var/log", "var/cache/pacman/pkg", ".snapshots", "boot"]:
        os.makedirs(f"/mnt/{d}", exist_ok=True)
    
    run(f"mount -o subvol=@home,{opts} {DISK}p3 /mnt/home")
    run(f"mount -o subvol=@log,{opts} {DISK}p3 /mnt/var/log")
    run(f"mount -o subvol=@pkg,{opts} {DISK}p3 /mnt/var/cache/pacman/pkg")
    run(f"mount -o subvol=@snapshots,{opts} {DISK}p3 /mnt/.snapshots")
    run(f"mount {DISK}p1 /mnt/boot")
    run(f"swapon {DISK}p2")

def configure_system():
    config_payload = f"""
# 1. Localization & Console
ln -sf /usr/share/zoneinfo/{TIMEZONE} /etc/localtime
hwclock --systohc
echo "{HOSTNAME}" > /etc/hostname
echo "en_US.UTF-8 UTF-8" > /etc/locale.gen
locale-gen
echo "LANG=en_US.UTF-8" > /etc/locale.conf
echo "KEYMAP=us" > /etc/vconsole.conf

# 2. Users & Passwords
echo "root:{TEMP_PW}" | chpasswd
useradd -m -G wheel -s /usr/bin/zsh {USER}
echo "{USER}:{TEMP_PW}" | chpasswd
echo "{USER} ALL=(ALL) ALL" >> /etc/sudoers

# 3. Zram Configuration
echo -e "[zram0]\\nzram-size = ram / 2\\ncompression-algorithm = zstd" > /etc/systemd/zram-generator.conf

# 4. XDG Base Directory Enforcement (System-wide)
echo 'export XDG_CONFIG_HOME="$HOME/.config"' >> /etc/zsh/zshenv
echo 'export XDG_CACHE_HOME="$HOME/.cache"' >> /etc/zsh/zshenv
echo 'export XDG_DATA_HOME="$HOME/.local/share"' >> /etc/zsh/zshenv
echo 'export XDG_STATE_HOME="$HOME/.local/state"' >> /etc/zsh/zshenv

# 5. Initcpio: Systemd hooks & AMD GPU Early Load
sed -i 's/^MODULES=(.*/MODULES=(amdgpu)/' /etc/mkinitcpio.conf
sed -i 's/^HOOKS=(.*/HOOKS=(systemd autodetect modconf kms keyboard sd-vconsole block filesystems)/' /etc/mkinitcpio.conf
mkinitcpio -p linux

# 6. Snapper Configuration (Sync with subvolume)
umount /.snapshots && rm -rf /.snapshots
snapper -c root create-config /
rm -rf /.snapshots && mkdir /.snapshots
mount -a
chown -R :wheel /.snapshots

# 7. Bootloader (GRUB)
grub-install --target=x86_64-efi --efi-directory=/boot --bootloader-id=GRUB
grub-mkconfig -o /boot/grub/grub.cfg

# 8. Enable System Services
systemctl enable NetworkManager
systemctl enable grub-btrfsd
systemctl enable snapper-timeline.timer
systemctl enable snapper-cleanup.timer

# Create initial baseline snapshot
snapper -c root create --description "Fresh Baseline Install" --type single
"""
    with open("/mnt/setup.sh", "w") as f:
        f.write(config_payload)
    run("arch-chroot /mnt bash /setup.sh")
    
    # 9. User-specific Zsh Config (Lean, XDG Compliant)
    zshrc = f"""
# Load standard plugins
source /usr/share/zsh/plugins/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
source /usr/share/zsh/plugins/zsh-autosuggestions/zsh-autosuggestions.zsh

# Completion cache in XDG Cache
autoload -Uz compinit
compinit -d "$XDG_CACHE_HOME/zsh/zcompdump-$ZSH_VERSION"

# History in XDG State
HISTFILE="$XDG_STATE_HOME/zsh/history"
HISTSIZE=2000
SAVEHIST=2000

alias ls='ls --color=auto'
alias grep='grep --color=auto'
"""
    # Ensure history directory exists for the user
    run(f"mkdir -p /mnt/home/{USER}/.local/state/zsh")
    with open(f"/mnt/home/{USER}/.zshrc", "w") as f:
        f.write(zshrc)
    
    # Set proper ownership for home directory
    run(f"arch-chroot /mnt chown -R {USER}:{USER} /home/{USER}")
    os.remove("/mnt/setup.sh")

if __name__ == "__main__":
    setup_partitions()
    print("Installing packages (pacstrap)...")
    run(f"pacstrap -K /mnt {' '.join(PACKAGES)}")
    run("genfstab -U /mnt >> /mnt/etc/fstab")
    configure_system()
    
    print("-" * 30)
    print(f"INSTALLATION COMPLETE.")
    print(f"Hostname: {HOSTNAME}")
    print(f"User:     {USER}")
    print(f"Password: {TEMP_PW}")
    print("-" * 30)
    print("Action Required: Reboot and run 'passwd' to secure your accounts.")
