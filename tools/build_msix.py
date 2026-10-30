"""MSIX paket za Microsoft Store od gotovog builda (python tools/build_release.py).

    python tools/build_msix.py [--dist <folder VideoDownload>] [--out <folder>]

Isti program kao instaler; Store paket za sada traži Windows 11 jer veza s browserom na Windowsu 10 nije provjerena.
Store ga potpisuje, instalira i ažurira, a program to sam
prepozna (`runtime.is_store_package`) i ne nudi naše ažuriranje (yt-dlp se i dalje osvježava sam).
Identitet je iz Partner Centera (Product identity, aplikacija „Video Download by abnps", Store ID 9NT46S6L7KGN).
Veza s browserom upisuje se u HKCU i %LOCALAPPDATA%, pa paket isključuje virtualizaciju registra i fajlova
(`unvirtualizedResources`; u napomeni za provjeru objasniti zašto).
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))

from videodl import __version__  # noqa: E402
from videodl.native_messaging import FIREFOX_REGISTRY_PATHS, REGISTRY_PATHS, STORE_HOST_ALIAS  # noqa: E402

BUILD = PROJECT.parent / "Build"
IDENTITY_NAME = "abnps.VideoDownloadbyabnps"
PUBLISHER = "CN=71819F50-D4A6-44BF-A0BC-D68768718275"
PUBLISHER_DISPLAY = "abnps"
DISPLAY_NAME = "Video Download by abnps"
LOGOS = {"Square44x44Logo.png": 44, "Square150x150Logo.png": 150, "StoreLogo.png": 50,
         "Square44x44Logo.targetsize-256_altform-unplated.png": 256}

# Stalna putanja hosta za browser: alias „abnps-videodl-host.exe" je na glavnoj aplikaciji, a pokreće videodl-host.exe.
# Posebna skrivena aplikacija (bez ikone u Startu) traži Microsoftovo odobrenje „HeadlessAppBypass" (odbijeno 20.10.2026).
MANIFEST = """<?xml version="1.0" encoding="utf-8"?>
<Package xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10"
         xmlns:uap="http://schemas.microsoft.com/appx/manifest/uap/windows10"
         xmlns:uap3="http://schemas.microsoft.com/appx/manifest/uap/windows10/3"
         xmlns:desktop="http://schemas.microsoft.com/appx/manifest/desktop/windows10"
         xmlns:rescap="http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities"
         xmlns:desktop6="http://schemas.microsoft.com/appx/manifest/desktop/windows10/6"
         xmlns:virtualization="http://schemas.microsoft.com/appx/manifest/virtualization/windows10"
         IgnorableNamespaces="uap uap3 desktop rescap desktop6 virtualization">
  <Identity Name="{name}" Publisher="{publisher}" Version="{version}" ProcessorArchitecture="x64" />
  <Properties>
    <DisplayName>{display}</DisplayName>
    <PublisherDisplayName>{publisher_display}</PublisherDisplayName>
    <Logo>Assets\\StoreLogo.png</Logo>
    <desktop6:RegistryWriteVirtualization>disabled</desktop6:RegistryWriteVirtualization>
    <desktop6:FileSystemWriteVirtualization>disabled</desktop6:FileSystemWriteVirtualization>
{excluded}
  </Properties>
  <Dependencies>
    <TargetDeviceFamily Name="Windows.Desktop" MinVersion="10.0.22000.0" MaxVersionTested="10.0.26100.0" />
  </Dependencies>
  <Resources>
    <Resource Language="en-us" /><Resource Language="bs" /><Resource Language="de" /><Resource Language="es" /><Resource Language="fr" />
  </Resources>
  <Applications>
    <Application Id="VideoDownload" Executable="VideoDownload.exe" EntryPoint="Windows.FullTrustApplication">
      <uap:VisualElements DisplayName="Video Download" Description="MP4 and MP3 downloader"
                          BackgroundColor="transparent" Square150x150Logo="Assets\\Square150x150Logo.png"
                          Square44x44Logo="Assets\\Square44x44Logo.png" />
      <Extensions>
        <uap3:Extension Category="windows.appExecutionAlias" Executable="{host_exe}"
                        EntryPoint="Windows.FullTrustApplication">
          <uap3:AppExecutionAlias>
            <desktop:ExecutionAlias Alias="{host_alias}" />
          </uap3:AppExecutionAlias>
        </uap3:Extension>
      </Extensions>
    </Application>
  </Applications>
  <Capabilities>
    <rescap:Capability Name="runFullTrust" />
    <rescap:Capability Name="unvirtualizedResources" />
  </Capabilities>
</Package>
"""


def excluded_locations() -> str:
    """Svako ime hosta i svaki browser dobijaju vlastiti izuzetak za upis u stvarni HKCU.

    Lokalna proba je potvrdila izuzetke za druga imena; za staro ime com.videodl.bridge
    upis ostaje virtualizovan iz zasad nepoznatog razloga.
    """
    keys = "".join(f"\n        <virtualization:ExcludedKey>HKEY_CURRENT_USER\\{path}</virtualization:ExcludedKey>"
                   for path in REGISTRY_PATHS + FIREFOX_REGISTRY_PATHS)
    return ("    <virtualization:FileSystemWriteVirtualization>\n"
            "      <virtualization:ExcludedDirectories>\n"
            # manifest za browser (native-host), bridge.json i postavke programa
            "        <virtualization:ExcludedDirectory>$(KnownFolder:LocalAppData)\\VideoDownload"
            "</virtualization:ExcludedDirectory>\n"
            "      </virtualization:ExcludedDirectories>\n"
            "    </virtualization:FileSystemWriteVirtualization>\n"
            "    <virtualization:RegistryWriteVirtualization>\n"
            f"      <virtualization:ExcludedKeys>{keys}\n"
            "      </virtualization:ExcludedKeys>\n"
            "    </virtualization:RegistryWriteVirtualization>")


def manifest(version: str) -> str:
    return MANIFEST.format(name=IDENTITY_NAME, publisher=PUBLISHER, version=version, display=DISPLAY_NAME,
                           publisher_display=PUBLISHER_DISPLAY, excluded=excluded_locations(),
                           host_exe="host\\videodl-host.exe", host_alias=STORE_HOST_ALIAS)  # paket je samo za Windows


def store_version(version: str) -> str:
    """Store traži četiri broja, a zadnji mora biti 0: 1.0.2 -> 1.0.2.0."""
    parts = version.split(".")[:3]
    parts += ["0"] * (3 - len(parts))
    return ".".join(parts + ["0"])


def find_makeappx() -> Path:
    kits = Path(r"C:\Program Files (x86)\Windows Kits\10\bin")
    found = sorted(kits.glob(r"*\x64\makeappx.exe"))
    if not found:
        raise SystemExit("makeappx.exe nije pronađen (instaliraj Windows SDK).")
    return found[-1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dist", type=Path, default=BUILD / "dist" / "VideoDownload")
    parser.add_argument("--out", type=Path, default=BUILD / "msix")
    args = parser.parse_args()
    if not (args.dist / "VideoDownload.exe").is_file():
        raise SystemExit(f"Nema gotovog builda u {args.dist} (prvo python tools/build_release.py).")

    from PIL import Image

    layout = args.out / "layout"
    shutil.rmtree(layout, ignore_errors=True)
    shutil.copytree(args.dist, layout)
    assets = layout / "Assets"
    assets.mkdir()
    icon = Image.open(PROJECT / "site" / "assets" / "icon.png").convert("RGBA")
    for name, size in LOGOS.items():
        icon.resize((size, size), Image.LANCZOS).save(assets / name)
    version = store_version(__version__)
    (layout / "AppxManifest.xml").write_text(manifest(version), encoding="utf-8")
    package = args.out / f"VideoDownloadbyabnps-{version}-x64.msix"
    subprocess.run([str(find_makeappx()), "pack", "/d", str(layout), "/p", str(package), "/o"], check=True,
                   stdout=subprocess.DEVNULL)
    print(f"MSIX: {package} ({package.stat().st_size / 1024 / 1024:.0f} MB) — postavi ga u Partner Center (nova prijava).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
