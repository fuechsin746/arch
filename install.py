import subprocess
import os

# --- Configuration ---
DISK = "/dev/nvme0n1"
HOSTNAME = "dell-dc15255"
USER = "bryanr"
TIMEZONE = "America/Chicago"
TEMP_PW = "temporary_password"

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
    run(f"sgdisk -Z {DISK}")
    run(f"sgdisk -n 1:0:+1G -t 1:ef00 {DISK}") # EFI
    run(f"sgdisk -n 2:0:+8G -t 2:8200 {DISK}") # Swap
    run(f"sgdisk -n 3:0:0 -t 3:8300 {DISK}")    # Btrfs

    run(f"mkfs.vfat -F32 {DISK}p1")
    run(f"mkswap {DISK}p2")
    run(f"mkfs.btrfs -f -L ARCH {DISK}p3")

    run(f"mount {DISK}p3 /mnt")
    for sv in ["@", "@home", "@log", "@pkg", "@snapshots"]:
        run(f"btrfs subvolume create /mnt/{sv}")
    run("umount /mnt")

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
    # Use triple quotes to avoid escape character errors in f-strings
    config_payload = f"""
ln -sf /usr/share/zoneinfo/{TIMEZONE} /etc/localtime
hwclock --systohc
echo "{HOSTNAME}" > /etc/hostname
echo "en_US.UTF-8 UTF-8" > /etc/locale.gen
locale-gen
echo "LANG=en_US.UTF-8" > /etc/locale.conf
echo "KEYMAP=us" > /etc/vconsole.conf

echo "root:{TEMP_PW}" | chpasswd
useradd -m -G wheel -s /usr/bin/zsh {USER}
echo "{USER}:{TEMP_PW}" | chpasswd
echo "{USER} ALL=(ALL) ALL" >> /etc/sudoers

echo -e "[zram0]\\nzram-size = ram / 2\\ncompression-algorithm = zstd" > /etc/systemd/zram-generator.conf

echo 'export XDG_CONFIG_HOME="$HOME/.config"' >> /etc/zsh/zshenv
echo 'export XDG_CACHE_HOME="$HOME/.cache"' >> /etc/zsh/zshenv
echo 'export XDG_DATA_HOME="$HOME/.local/share"' >> /etc/zsh/zshenv
echo 'export XDG_STATE_HOME="$HOME/.local/state"' >> /etc/zsh/zshenv

sed -i 's/^MODULES=(.*/MODULES=(amdgpu)/' /etc/mkinitcpio.conf
sed -i 's/^HOOKS=(.*/HOOKS=(systemd autodetect modconf kms keyboard sd-vconsole block filesystems)/' /etc/mkinitcpio.conf
mkinitcpio -p linux

umount /.snapshots && rm -rf /.snapshots
snapper -c root create-config /
rm -rf /.snapshots && mkdir /.snapshots
mount -a
chown -R :wheel /.snapshots

grub-install --target=x86_64-efi --efi-directory=/boot --bootloader-id=GRUB
grub-mkconfig -o /boot/grub/grub.cfg

systemctl enable NetworkManager grub-btrfsd snapper-timeline.timer snapper-cleanup.timer
snapper -c root create --description "Post-Install Base" --type single
"""
    with open("/mnt/setup.sh", "w") as f:
        f.write(config_payload)
    run("arch-chroot /mnt bash /setup.sh")
    
    # Corrected Zshrc handling using triple quotes
    zshrc_content = """
source /usr/share/zsh/plugins/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
source /usr/share/zsh/plugins/zsh-autosuggestions/zsh-autosuggestions.zsh
autoload -Uz compinit
compinit -d "$XDG_CACHE_HOME/zsh/zcompdump-$ZSH_VERSION"
HISTFILE="$XDG_STATE_HOME/zsh/history"
HISTSIZE=2000
SAVEHIST=2000
alias ls='ls --color=auto'
"""
    run(f"mkdir -p /mnt/home/{USER}/.local/state/zsh")
    with open(f"/mnt/home/{USER}/.zshrc", "w") as f:
        f.write(zshrc_content)
    
    run(f"arch-chroot /mnt chown -R {USER}:{USER} /home/{USER}")
    os.remove("/mnt/setup.sh")

if __name__ == "__main__":
    setup_partitions()
    run(f"pacstrap -K /mnt {' '.join(PACKAGES)}")
    run("genfstab -U /mnt >> /mnt/etc/fstab")
    configure_system()
    print(f"DONE. User: {USER}, Password: {TEMP_PW}")
