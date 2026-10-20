"""Pripremi razvojni MSIX za jednokratnu probu posebnog imena hosta u tri HKCU ključa.

    python tools/prepare_store_registry_probe.py [--out <folder van projekta>]

Samo kopira reg.exe i piše manifest u Build. Registracija i čišćenje su zasebni,
opisani u 00_plan/store_browser_link_probe.md.
"""

import argparse
import shutil
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = PROJECT.parent / "Build" / "store-registry-probe" / "DisposableHost"
PUBLISHER = "CN=71819F50-D4A6-44BF-A0BC-D68768718275"
PACKAGE_NAME = "abnps.VideoDownloadDisposableHostProbe"
# Namjerno različito od imena u izdanju: brisanje probnog ključa može promijeniti
# ponašanje MSIX virtualizacije pri ponovnom upisu iste putanje.
PROBE_HOST_NAME = "io.github.abnps.registryprobe"
REGISTRY_PATHS = {
    "Chrome": rf"Software\Google\Chrome\NativeMessagingHosts\{PROBE_HOST_NAME}",
    "Edge": rf"Software\Microsoft\Edge\NativeMessagingHosts\{PROBE_HOST_NAME}",
    "Firefox": rf"Software\Mozilla\NativeMessagingHosts\{PROBE_HOST_NAME}",
}


def manifest() -> str:
    keys = "\n".join(
        f"      <virtualization:ExcludedKey>HKEY_CURRENT_USER\\{path}</virtualization:ExcludedKey>"
        for path in REGISTRY_PATHS.values()
    )
    apps = "\n".join(f'''
    <Application Id="{browser}" Executable="reg.exe" EntryPoint="Windows.FullTrustApplication"
                 uap10:Parameters="add HKCU\\{path} /v ABNPSProbe /t REG_SZ /d visible /f">
      <uap:VisualElements DisplayName="ABNPS Probe {browser}" Description="Local HKCU test"
                          BackgroundColor="transparent" Square150x150Logo="Assets\\Square150x150Logo.png"
                          Square44x44Logo="Assets\\Square44x44Logo.png" />
    </Application>'''
                     for browser, path in REGISTRY_PATHS.items())
    return f'''<?xml version="1.0" encoding="utf-8"?>
<Package xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10"
         xmlns:uap="http://schemas.microsoft.com/appx/manifest/uap/windows10"
         xmlns:uap10="http://schemas.microsoft.com/appx/manifest/uap/windows10/10"
         xmlns:desktop6="http://schemas.microsoft.com/appx/manifest/desktop/windows10/6"
         xmlns:virtualization="http://schemas.microsoft.com/appx/manifest/virtualization/windows10"
         xmlns:rescap="http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities"
         IgnorableNamespaces="uap uap10 desktop6 virtualization rescap">
  <Identity Name="{PACKAGE_NAME}" Publisher="{PUBLISHER}" Version="1.0.0.0" ProcessorArchitecture="x64" />
  <Properties>
    <DisplayName>ABNPS New Host Probe</DisplayName>
    <PublisherDisplayName>abnps</PublisherDisplayName>
    <Logo>Assets\\StoreLogo.png</Logo>
    <desktop6:RegistryWriteVirtualization>disabled</desktop6:RegistryWriteVirtualization>
    <virtualization:RegistryWriteVirtualization><virtualization:ExcludedKeys>
{keys}
    </virtualization:ExcludedKeys></virtualization:RegistryWriteVirtualization>
  </Properties>
  <Dependencies><TargetDeviceFamily Name="Windows.Desktop" MinVersion="10.0.19041.0"
                                    MaxVersionTested="10.0.26100.0" /></Dependencies>
  <Resources><Resource Language="en-us" /></Resources>
  <Applications>{apps}
  </Applications>
  <Capabilities><rescap:Capability Name="runFullTrust" />
                <rescap:Capability Name="unvirtualizedResources" /></Capabilities>
</Package>
'''


def prepare(out: Path) -> None:
    from PIL import Image

    reg = Path(r"C:\Windows\System32\reg.exe")
    if not reg.is_file():
        raise SystemExit("reg.exe nije pronađen; ova proba se pokreće samo na Windowsu.")
    assets = out / "Assets"
    assets.mkdir(parents=True, exist_ok=True)
    shutil.copy2(reg, out / "reg.exe")
    with Image.open(PROJECT / "site" / "assets" / "icon.png") as source:
        icon = source.convert("RGBA")
    for name, size in (("StoreLogo.png", 50), ("Square44x44Logo.png", 44), ("Square150x150Logo.png", 150)):
        icon.resize((size, size), Image.Resampling.LANCZOS).save(assets / name)
    (out / "AppxManifest.xml").write_text(manifest(), encoding="utf-8")
    print(out / "AppxManifest.xml")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    if PROJECT == args.out.resolve() or PROJECT in args.out.resolve().parents:
        raise SystemExit("Izlaz mora biti van foldera projekta.")
    prepare(args.out)


if __name__ == "__main__":
    main()
