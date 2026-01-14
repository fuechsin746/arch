#!/usr/bin/env python3
import subprocess, os, sys, glob, getpass

def get_input(prompt, default=""):
    val = input(f"{prompt} [{default}]: ").strip()
    return val if val else default

def get_password(prompt):
    while True:
        pw = getpass.getpass(f"{prompt}: ")
        conf = getpass.getpass(f"Confirm {prompt}: ")
        if pw == conf and pw != "": return pw
        print(">> Passwords do not match.")

def run(cmd, input_data=None):
    print(f"--> [RUNNING]: {cmd}")
    return subprocess.run(cmd, shell=True, check=True, text=True, input=input_data)

if __name__ == "__main__":
    print("=== ARCH LINUX BASE INSTALLER (CLI + XDG) ===")
    
    kbd  = get_input("Keyboard Layout", "us")
    host = get_input("Hostname", "dell-arch")
    user = get_input("Username", "bryanr")
    tz   = get_input("Timezone", "America/Chicago")
    pw   = get_password("System Password")
    
    disks = glob.glob("/dev/nvme[0-9]n[1-9]") or glob.glob("/dev/sd[a-z]")
    disk = disks[0]
    
    # 1. Standard Partitioning & Btrfs Setup (Abbreviated for brevity, same as previous)
    run(f"sgdisk -Z {disk}")
    run(f"sgdisk -n 1:0:+1G -t 1:ef00 {disk}")
    run(f"sgdisk -n 2:0:+8G -t 2:8200 {disk}")
    run(f"sgdisk -n 3:0:0 -t 3:8300 {disk}")
    part = "p" if "nvme" in disk else ""
    run(f"mkfs.vfat -F32 {disk}{part}1")
    run(f"mkswap -f {disk}{part}2")
    run(f"mkfs.btrfs -f -L ARCH {disk}{part}3")
    run(f"mount {disk}{part}3 /mnt")
    for sv in ["@", "@home", "@log", "@pkg", "@snapshots"]:
        run(f"btrfs subvolume create /mnt/{sv}")
    run("umount /mnt")
    opts = "noatime,compress=zstd,commit=120"
    run(f"mount -o subvol=@,{opts} {disk}{part}3 /mnt")
    for d in ["home", "var/log", "var/cache/pacman/pkg", ".snapshots", "boot"]:
        os.makedirs(f"/mnt/{d}", exist_ok=True)
    run(f"mount -o subvol=@home,{opts} {disk}{part}3 /mnt/home")
    run(f"mount -o subvol=@log,{opts} {disk}{part}3 /mnt/var/log")
    run(f"mount -o subvol=@pkg,{opts} {disk}{part}3 /mnt/var/cache/pacman/pkg")
    run(f"mount -o subvol=@snapshots,{opts} {disk}{part}3 /mnt/.snapshots")
    run(f"mount {disk}{part}1 /mnt/boot")
    run(f"swapon {disk}{part}2")

    # 2. Pacstrap (Adding xdg-user-dirs, nano, vim)
    pkgs = ["base", "linux", "linux-firmware", "amd-ucode", "base-devel", "networkmanager", 
            "zsh", "grub", "efibootmgr", "os-prober", "snapper", "grub-btrfs", "mesa", 
            "libinput", "reflector", "xdg-user-dirs", "nano", "vim", "btrfs-progs", "ntfs-3g"]
    run(f"pacstrap -K /mnt {' '.join(pkgs)}")
    run("genfstab -U /mnt >> /mnt/etc/fstab")

    # 3. Chroot Configuration (The "Pro" Setup)
    final_cmds = f"""
ln -sf /usr/share/zoneinfo/{tz} /etc/localtime
hwclock --systohc
echo "en_US.UTF-8 UTF-8" > /etc/locale.gen
locale-gen
echo "LANG=en_US.UTF-8" > /etc/locale.conf
echo "KEYMAP={kbd}" >> /etc/vconsole.conf
echo "{host}" > /etc/hostname

# --- XDG Base Directory Global Setup ---
cat <<EOF >> /etc/environment
XDG_CONFIG_HOME=\\$HOME/.config
XDG_CACHE_HOME=\\$HOME/.cache
XDG_DATA_HOME=\\$HOME/.local/share
XDG_STATE_HOME=\\$HOME/.local/state
EOF

# --- User Setup ---
useradd -m -G wheel -s /usr/bin/zsh {user}
echo "root:{pw}" | chpasswd
echo "{user}:{pw}" | chpasswd
echo "{user} ALL=(ALL) ALL" >> /etc/sudoers

# --- ZSH Global Config (ZDOTDIR) ---
# We force Zsh to look in ~/.config/zsh
echo 'export ZDOTDIR="\\$HOME/.config/zsh"' >> /etc/zsh/zshenv
mkdir -p /home/{user}/.config/zsh
cat <<EOF > /home/{user}/.config/zsh/.zshrc
export HISTFILE="\\$XDG_STATE_HOME/zsh_history"
export HISTSIZE=1000
export SAVEHIST=1000
setopt APPEND_HISTORY
bindkey -e
# Basic Prompt
PROMPT='%F{{cyan}}%n@%m %F{{blue}}%~ %F{{yellow}}%% %f'
alias vim="vim -u \\$XDG_CONFIG_HOME/vim/vimrc"
EOF

# --- Nano & Vim XDG Fixes ---
mkdir -p /home/{user}/.config/{{nano,vim}}
echo 'set historylog' > /home/{user}/.config/nano/nanorc
echo 'set backupdir="~/.local/share/nano/backups"' >> /home/{user}/.config/nano/nanorc

cat <<EOF > /home/{user}/.config/vim/vimrc
set runtimepath+=\\$XDG_CONFIG_HOME/vim
set runtimepath+=\\$XDG_DATA_HOME/vim
set runtimepath+=\\$XDG_DATA_HOME/vim/after
set runtimepath+=\\$XDG_CONFIG_HOME/vim/after
let &directory = \\$XDG_DATA_HOME . '/vim/swap//'
let &backupdir = \\$XDG_DATA_HOME . '/vim/backup//'
let &undodir   = \\$XDG_DATA_HOME . '/vim/undo//'
set nocompatible
syntax on
EOF

chown -R {user}:{user} /home/{user}/.config

# --- System Finalization ---
sed -i 's/^MODULES=(.*/MODULES=(amdgpu)/' /etc/mkinitcpio.conf
mkinitcpio -p linux
grub-install --target=x86_64-efi --efi-directory=/boot --bootloader-id=GRUB
grub-mkconfig -o /boot/grub/grub.cfg
systemctl enable NetworkManager grub-btrfsd snapper-timeline.timer
"""
    run("arch-chroot /mnt /bin/bash", input_data=final_cmds)

    # Trigger xdg-user-dirs for the user on first login
    run(f"arch-chroot /mnt /bin/bash -c 'sudo -u {user} xdg-user-dirs-update'")

    print("\n[DONE] XDG Base Directories and tool configs are set. Reboot.")
