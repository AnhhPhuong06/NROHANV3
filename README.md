# NroHan iOS

Project Xcode export từ Unity 2021.3.45f2, dành cho iPhone/iPad arm64.

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

Tham khảo: [Codemagic YAML](https://docs.codemagic.io/yaml-basic-configuration/yaml-getting-started/)
và [build iOS unsigned](https://docs.codemagic.io/yaml-quick-start/first-signed-build/).
