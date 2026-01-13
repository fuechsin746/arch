#!/usr/bin/env python3
import subprocess, os, sys, glob

# Ensures whiptail can always find a terminal to draw on
os.environ['TERM'] = 'linux'

def inputbox(title, prompt, default=""):
    try:
        # Added explicit TTY attachment to prevent hanging
        cmd = f'whiptail --title "{title}" --inputbox "{prompt}" 10 60 "{default}" 3>&1 1>&2 2>&3'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            sys.exit(0)
        return result.stdout.strip()
    except Exception as e:
        print(f"UI Error: {e}")
        return input(f"{prompt} [{default}]: ") or default

def passwordbox(title, prompt):
    while True:
        pw_cmd = f'whiptail --title "{title}" --passwordbox "{prompt}" 10 60 3>&1 1>&2 2>&3'
        pw = subprocess.run(pw_cmd, shell=True, capture_output=True, text=True).stdout.strip()
        
        conf_cmd = f'whiptail --title "{title}" --passwordbox "Confirm {prompt}" 10 60 3>&1 1>&2 2>&3'
        confirm = subprocess.run(conf_cmd, shell=True, capture_output=True, text=True).stdout.strip()
        
        if pw == confirm and pw != "": 
            return pw
        
        subprocess.run('whiptail --msgbox "Passwords do not match or empty! Try again." 10 60', shell=True)

def run(cmd, input_data=None):
    # Print what we are doing so if it hangs here, you know exactly which command failed
    print(f"--> [RUNNING]: {cmd}")
    subprocess.run(cmd, shell=True, check=True, text=True, input=input_data)

def setup_partitions(disk):
    print(f"--> Partitioning {disk}...")
    # Clear partition table
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

def configure_base(host, user, tz, pw):
    chroot_cmds = f"""
ln -sf /usr/share/zoneinfo/{tz} /etc/localtime
hwclock --systohc
echo "{host}" > /etc/hostname
echo "en_US.UTF-8 UTF-8" > /etc/locale.gen
locale-gen
echo "LANG=en_US.UTF-8" > /etc/locale.conf
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
systemctl enable NetworkManager grub-btrfsd snapper-timeline.timer
"""
    run("arch-chroot /mnt /bin/bash", input_data=chroot_cmds)

if __name__ == "__main__":
    # Immediate feedback to ensure script is alive
    print("Initializing Arch Installer...")
    
    host = inputbox("Hostname", "Enter system name:", "dell-arch")
    user = inputbox("Username", "Enter user:", "bryanr")
    tz = inputbox("Timezone", "e.g. America/Chicago:", "America/Chicago")
    pw = passwordbox("Security", "Enter password for root/user:")
    
    # Drive Detection
    disk_list = glob.glob("/dev/nvme[0-9]n[1-9]")
    if not disk_list:
        # Fallback to standard SATA if NVMe is not found
        disk_list = glob.glob("/dev/sd[a-z]")
        
    if not disk_list:
        sys.exit("Critical Error: No usable drive found!")
        
    disk = disk_list[0]
    print(f"Target Disk identified: {disk}")
    
    setup_partitions(disk)
    fs = ["btrfs-progs", "xfsprogs", "f2fs-tools", "dosfstools", "e2fsprogs", "ntfs-3g"]
    pkgs = ["base", "linux", "linux-firmware", "amd-ucode", "base-devel", "networkmanager", "zsh", "grub", "efibootmgr", "os-prober", "snapper", "grub-btrfs", "mesa", "libinput"] + fs
    
    print("\nStarting Pacstrap (Downloading base packages)...")
    run(f"pacstrap -K /mnt {' '.join(pkgs)}")
    run("genfstab -U /mnt >> /mnt/etc/fstab")
    configure_base(host, user, tz, pw)
    
    print("\n[SUCCESS] Base Install Done. Reboot and run setup_gui.py")
