"""Package the static install site and signed IPA for an existing HTTPS VPS."""

import argparse
import fnmatch
import hashlib
import plistlib
import re
import shutil
import zipfile
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import quote, unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
GITHUB_SITE = "https://anhhphuong06.github.io/NROHANV3/"


def build_package(base_url, ipa, output):
    url = urlsplit(base_url)
    parts = unquote(url.path).strip("/").split("/") if url.path.strip("/") else []
    if (
        url.scheme != "https" or not url.hostname or url.username or url.password
        or url.query or url.fragment or not base_url.endswith("/")
        or any(part in ("", ".", "..") or not re.fullmatch(r"[A-Za-z0-9._~-]+", part) for part in parts)
    ):
        raise ValueError("Use a full HTTPS URL ending with /, without credentials or query parameters.")

    source = ROOT / "docs"
    ipa = ipa.resolve(strict=True)
    output = output.resolve()
    if output == source.resolve() or source.resolve() in output.parents:
        raise ValueError("Output must be separate from the docs source directory.")
    with zipfile.ZipFile(ipa) as archive:
        names = archive.namelist()
        info_files = [n for n in names if n.startswith("Payload/") and n.count("/") == 2 and n.endswith("/Info.plist")]
        if len(info_files) != 1:
            raise ValueError("Expected one app in the IPA.")
        app = info_files[0].rsplit("/", 1)[0]
        if app + "/embedded.mobileprovision" not in names or app + "/_CodeSignature/CodeResources" not in names:
            raise ValueError("Use an IPA with an embedded profile and signature resources.")
        info = plistlib.loads(archive.read(info_files[0]))
        profile_bytes = archive.read(app + "/embedded.mobileprovision")
        start, end = profile_bytes.find(b"<?xml"), profile_bytes.find(b"</plist>")
        if start < 0 or end < start:
            raise ValueError("Cannot read the embedded provisioning profile.")
        profile = plistlib.loads(profile_bytes[start:end + 8])
        pattern = profile["Entitlements"]["application-identifier"].partition(".")[2]
        if not profile.get("ProvisionsAllDevices") or not fnmatch.fnmatchcase(info["CFBundleIdentifier"], pattern):
            raise ValueError("Use an Enterprise IPA with a profile matching its bundle ID.")
        expiry = profile["ExpirationDate"].replace(tzinfo=timezone.utc)
        if expiry <= datetime.now(timezone.utc):
            raise ValueError("The IPA provisioning profile has expired. Re-sign before packaging.")

    manifest = plistlib.loads((source / "manifest.plist").read_bytes())
    item = manifest["items"][0]
    old_ipa_url = item["assets"][0]["url"]
    item["assets"][0]["url"] = base_url + "NroHan-enterprise.ipa"
    item["metadata"]["bundle-identifier"] = info["CFBundleIdentifier"]
    item["metadata"]["bundle-version"] = info["CFBundleVersion"]
    html = (source / "index.html").read_text(encoding="utf-8")
    old_install = quote(GITHUB_SITE + "manifest.plist", safe="")
    if old_install not in html or old_ipa_url not in html:
        raise ValueError("The install page template no longer matches the source manifest.")
    html = html.replace(old_install, quote(base_url + "manifest.plist", safe=""))
    html = html.replace(GITHUB_SITE, base_url).replace(old_ipa_url, "NroHan-enterprise.ipa")

    # Write only known deployment files, preserving other files in the output.
    public = output / "upload"
    site = public.joinpath(*parts)
    site.mkdir(parents=True, exist_ok=True)
    (site / "index.html").write_text(html, encoding="utf-8")
    (site / "manifest.plist").write_bytes(plistlib.dumps(manifest, sort_keys=False))
    (site / "assets").mkdir(exist_ok=True)
    shutil.copy2(source / "assets/app-icon.png", site / "assets/app-icon.png")
    shutil.copy2(ipa, site / "NroHan-enterprise.ipa")
    (site / ".htaccess").write_text(
        "<IfModule mod_mime.c>\n"
        "  AddType text/xml .plist\n"
        "  AddType application/octet-stream .ipa\n"
        "</IfModule>\n", encoding="ascii",
    )
    files = [site / name for name in (
        "index.html", "manifest.plist", "assets/app-icon.png", "NroHan-enterprise.ipa", ".htaccess",
    )]
    package = output / "NroHan-VPS.zip"
    instructions = f"""ĐƯA TRANG CÀI NROHAN LÊN VPS

1. Upload NroHan-VPS.zip vào thư mục gốc của website đang phục vụ tên miền.
2. Giải nén tại thư mục gốc website. Chỉ các file thuộc đường dẫn {url.path or '/'} được thêm vào.
   Không thay index.php/index.html của website cũ ở thư mục gốc nếu dùng /ios/.
3. Mở {base_url} bằng Safari trên iPhone / iPad.

URL manifest: {base_url}manifest.plist
URL IPA: {base_url}NroHan-enterprise.ipa

Đây là website tĩnh: không cần cài Node.js, PHP hoặc database.
Có thể chép trực tiếp toàn bộ nội dung thư mục upload/ lên thư mục gốc website.
Giữ DNS trỏ tới VPS. Không cần trỏ tên miền sang GitHub Pages.

HTTPS phải hợp lệ; trang, manifest và IPA phải truy cập được không cần đăng nhập.
Apache: gói đã có .htaccess khai báo MIME cho .plist và .ipa.
Nginx: bảo đảm .plist có MIME text/xml, .ipa có MIME application/octet-stream.
Nếu cần, thêm nội dung nginx-ios.conf vào khối server của website hiện tại,
kiểm tra bằng nginx -t rồi reload Nginx. Cấu hình dùng root hiện có của website.
Thư mục nên có quyền đọc file cho web server; thông thường thư mục 755, file 644.
Không upload thư mục chungchi/, file .p12 hoặc mật khẩu lên website.

IPA phiên bản {info.get('CFBundleShortVersionString', '')}.
Profile bản hiện tại hết hạn ngày {expiry:%d/%m/%Y}.
Chưa kiểm tra trực tiếp trên VPS của bạn hoặc cài trên iPhone thực tế.
"""
    (output / "HUONG-DAN.txt").write_text(instructions, encoding="utf-8-sig")
    nginx_path = "/" + "/".join(parts) + "/" if parts else "/"
    (output / "nginx-ios.conf").write_text(
        "# Add inside the existing server {} for this website.\n"
        "# Inherits the existing document root; use the same path as --base-url.\n"
        f"location ^~ {nginx_path} {{\n"
        "    index index.html;\n"
        "    types {\n"
        "        text/html html;\n"
        "        text/xml plist;\n"
        "        image/png png;\n"
        "        application/octet-stream ipa;\n"
        "    }\n"
        "    try_files $uri $uri/ =404;\n"
        "}\n", encoding="ascii",
    )
    deploy_notes = site / "_deploy"
    deploy_notes.mkdir(exist_ok=True)
    for name in ("HUONG-DAN.txt", "nginx-ios.conf"):
        target = deploy_notes / name
        shutil.copy2(output / name, target)
        files.append(target)
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
        for file in files:
            archive.write(file, file.relative_to(public).as_posix())
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    (output / "SHA256SUMS.txt").write_text(f"{digest}  {package.name}\n", encoding="ascii")
    print(f"Package: {package}")
    print(f"Ready-to-upload files: {public}")
    print(f"Installation URL: {base_url}")
    return package


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="https://nroha.fun/ios/")
    parser.add_argument("--ipa", type=Path, default=ROOT / "IPA/NroHan-enterprise.ipa")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "VPS")
    args = parser.parse_args()
    build_package(args.base_url, args.ipa, args.output_dir)


if __name__ == "__main__":
    main()
