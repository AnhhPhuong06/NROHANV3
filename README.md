# NroHan iOS

Project Xcode export từ Unity 2021.3.45f2, dành cho iPhone/iPad arm64.

## Cài đặt trên iPhone / iPad

Mở [trang cài NroHan](https://anhhphuong06.github.io/NROHANV3/) bằng Safari.
Trang và manifest OTA ở `docs/`; IPA đã ký được lưu ở GitHub Releases.
Profile của bản Enterprise 0.0.3 hiện tại hết hạn ngày **05/11/2026**.

## Build IPA unsigned trên Codemagic

1. Mở app liên kết với repo `AnhhPhuong06/NROHANV3` trên Codemagic.
2. Chọn **Start new build**, nhánh **main**, workflow **ios-unsigned**
   (**NroHan - Unsigned IPA**). Nếu app đang dùng Workflow Editor, chuyển sang
   cấu hình bằng `codemagic.yaml` ở gốc repo.
3. Sau khi build thành công, tải **NroHan-unsigned.ipa** trong **Artifacts**.
   Log Xcode và result bundle cũng được lưu để kiểm tra khi build lỗi.

Workflow dùng máy Mac mini M2 với Xcode 16.4, build cấu hình Release cho thiết bị
iOS arm64, tắt code signing và bitcode, rồi đóng gói app vào `Payload/*.app`.
Không cần certificate, provisioning profile hay tài khoản Apple Developer cho
bước tạo IPA unsigned. IPA cần được ký trước khi cài lên thiết bị iOS thông thường.

Các thư viện `Libraries/*.a` được lưu bằng Git LFS. Workflow tự tải chúng trước
khi build; không xóa hoặc thay các thư viện này bằng file pointer.

## Build trên máy Mac

```bash
git lfs install
git clone https://github.com/AnhhPhuong06/NROHANV3.git
cd NROHANV3
git lfs pull
bash ci/build_unsigned_ipa.sh
```

Kết quả: `build/NroHan-unsigned.ipa`.

## Build IPA ký Enterprise trên Codemagic

Trong **Team settings → codemagic.yaml settings → Code signing identities**:

1. Tab **iOS certificates**: tải file `.p12` chứa certificate và private key,
   nhập mật khẩu trực tiếp vào Codemagic, đặt Reference name là
   **nrohan_enterprise_cert**.
2. Tab **iOS provisioning profiles**: tải `.mobileprovision`, đặt Reference name
   là **nrohan_enterprise_profile**. Profile phải là loại **Enterprise / In House**,
   còn hạn và có dấu kiểm khớp với certificate.
3. Chạy workflow **ios-enterprise** trên nhánh **main**.
4. Tải **NroHan-enterprise.ipa** trong **Artifacts** sau khi build thành công.

Workflow dùng Bundle ID cụ thể trong profile. Với profile wildcard `*`, giữ
`com.DefaultCompany.Boy003`; với wildcard có prefix khác, ví dụ `com.company.*`,
dùng `com.company.NroHan`. Có thể đặt biến **BUNDLE_ID** trong app settings trên
Codemagic để chọn ID khác phù hợp với profile. Thay đổi Bundle ID chỉ áp dụng
trong checkout của lượt build Enterprise.

Chứng chỉ, private key, mật khẩu và profile được quản lý trong Codemagic,
không đưa vào GitHub. Bản ký Enterprise dành cho phân phối nội bộ của tổ chức.
Workflow tạo IPA đã ký; việc lưu trữ file và tạo link cài OTA được thiết lập riêng.

Tham khảo: [Code signing trên Codemagic](https://docs.codemagic.io/yaml-code-signing/signing-ios/).

Tham khảo: [Codemagic YAML](https://docs.codemagic.io/yaml-basic-configuration/yaml-getting-started/)
và [build iOS unsigned](https://docs.codemagic.io/yaml-quick-start/first-signed-build/).
