import platform
import subprocess
import sys

print("=== SYSTEM INFO ===")
print("Python Version:", sys.version)
print("Platform:", platform.platform())
print("Machine:", platform.machine())
print("Processor:", platform.processor())

# Verifica se o disco e SSD via PowerShell Get-PhysicalDisk
print("\n=== DISK MEDIA TYPE (SSD / HDD) ===")
try:
    ps_cmd = "Get-PhysicalDisk | Select-Object FriendlyName, MediaType, BusType, @{Name='Size_GB';Expression={[math]::round($_.Size/1GB,2)}} | Format-Table -AutoSize"
    out = subprocess.check_output(["powershell", "-NoProfile", "-Command", ps_cmd], text=True, stderr=subprocess.STDOUT)
    print(out.strip())
except Exception as e:
    print(f"NÃO VERIFICADO (erro: {e})")
