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
        print(">> Passwords do not match. Try again.")

def run(cmd, input_data=None):
    print(f"--> [RUNNING]: {cmd}")
    return subprocess.run(cmd, shell=True, check=True, text=True, input=input_data)

if __name__ == "__main__":
    print("=== ARCH LINUX BASE INSTALLER (CLI) ===")
    
    # 1. Inputs
    kbd  = get_input("Keyboard Layout", "us")
    host = get_input("Hostname", "dell-arch")
    user = get_input("Username", "bryanr")
    tz   = get_input("Timezone", "America/Chicago")
    pw   = get_password("System Password")
    
    run(f"loadkeys {kbd}")
    
    # 2. Disk Detection
    disks = glob.glob("/dev/nvme[0-9]n[1-9]") or glob.glob("/dev/sd[a-z]")
    if not disks: sys.exit("No drive detected.")
    disk = disks[0]
    
    print(f"\nWARNING: ALL DATA ON {disk} WILL BE ERASED!")
    confirm = input(f"Type 'YES' to format {disk}: ")
    if confirm != "YES": sys.exit("Aborted.")

    # 3. Mirrors & Partitioning
    print("--> Optimizing mirrors...")
    run("reflector --latest 10 --protocol https --sort rate --save /etc/pacman.d/mirrorlist")
    
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
    
    # 4. Pacstrap & Chroot
    fs = ["btrfs-progs", "xfsprogs", "f2fs-tools", "dosfstools", "e2fsprogs", "ntfs-3g"]
    pkgs = ["base", "linux", "linux-firmware", "amd-ucode", "base-devel", "networkmanager", "zsh", "grub", "efibootmgr", "os-prober", "snapper", "grub-btrfs", "mesa", "libinput", "reflector"] + fs
    run(f"pacstrap -K /mnt {' '.join(pkgs)}")
    run("genfstab -U /mnt >> /mnt/etc/fstab")
    
    final_cmds = f"""
ln -sf /usr/share/zoneinfo/{tz} /etc/localtime
hwclock --systohc
echo "en_US.UTF-8 UTF-8" > /etc/locale.gen
locale-gen
echo "LANG=en_US.UTF-8" > /etc/locale.conf
echo "KEYMAP={kbd}" >> /etc/vconsole.conf
echo "{host}" > /etc/hostname
echo "root:{pw}" | chpasswd
useradd -m -G wheel -s /usr/bin/zsh {user}
echo "{user}:{pw}" | chpasswd
echo "{user} ALL=(ALL) ALL" >> /etc/sudoers
sed -i 's/^MODULES=(.*/MODULES=(amdgpu)/' /etc/mkinitcpio.conf
sed -i 's/^HOOKS=(.*/HOOKS=(base systemd autodetect modconf kms keyboard sd-vconsole block filesystems fsck)/' /etc/mkinitcpio.conf
mkinitcpio -p linux
echo "GRUB_DISABLE_OS_PROBER=false" >> /etc/default/grub
grub-install --target=x86_64-efi --efi-directory=/boot --bootloader-id=GRUB
grub-mkconfig -o /boot/grub/grub.cfg
systemctl enable NetworkManager grub-btrfsd snapper-timeline.timer reflector.timer
"""
    run("arch-chroot /mnt /bin/bash", input_data=final_cmds)
    print("\n[DONE] Base system ready. Reboot and run setup_gui.py")
