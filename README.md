# Arch Linux on Dell 15 (dc15255)

Automated Arch Linux installation script optimized for the **AMD Ryzen 3 7320u** (Mendocino) with Radeon 610M graphics. This setup focuses on system stability via Btrfs snapshots, XDG Base Directory compliance, and a lean Zsh environment.

## 💻 Hardware Specs
- **Model:** Dell 15 dc15255
- **CPU:** AMD Ryzen 3 7320u
- **RAM:** 8 GiB
- **Disk:** 512 GB NVMe (`/dev/nvme0n1`)

## 🛠️ System Architecture

### Partitioning & Subvolumes
The disk is partitioned using GPT with a focus on Btrfs subvolumes to allow for atomic system rollbacks without affecting user data or system logs.



| Partition | Size | Format | Mount Point | Subvolume |
| :--- | :--- | :--- | :--- | :--- |
| `nvme0n1p1` | 1 GiB | FAT32 | `/boot` | — |
| `nvme0n1p2` | 8 GiB | Swap | `[SWAP]` | — |
| `nvme0n1p3` | 467 GiB| Btrfs | `/` | `@` |
| `nvme0n1p3` | — | Btrfs | `/home` | `@home` |
| `nvme0n1p3` | — | Btrfs | `/.snapshots`| `@snapshots` |
| `nvme0n1p3` | — | Btrfs | `/var/log` | `@log` |
| `nvme0n1p3` | — | Btrfs | `/var/cache`| `@pkg` |

### Key Features
- **Snapshots:** `Snapper` configured with `grub-btrfs` for bootable snapshots directly from the GRUB menu.
- **AMD Optimization:** Includes `amd-ucode`, `mesa`, and `amdgpu` kernel modules.
- **Memory:** Hybrid 8 GiB Physical Swap + ZRAM (Half of RAM) using `zram-generator`.
- **XDG Compliance:** All Zsh configs and history are moved out of the home root to `~/.config`, `~/.cache`, and `~/.local`.
- **Init:** Modern `systemd` hooks in `mkinitcpio.conf`.

## 🚀 Deployment
1. Boot the Arch ISO.
2. Connect to the internet (use `iwctl` for WiFi).
3. Run the installer directly from this repo:
   ```bash
   curl -L https://raw.githubusercontent.com/fuechsin746/arch/main/install.py -o install.py
   python install.py
