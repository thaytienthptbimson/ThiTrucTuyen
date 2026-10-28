# THITRUCTUYEN — gói đóng gói ứng dụng

Gói này do công cụ **Đóng gói ứng dụng** tạo ra. Việc biên dịch diễn ra trên máy chủ miễn phí của GitHub (GitHub Actions), bạn không cần cài Android Studio, Visual Studio hay Xcode.

## Các tệp trong gói

| Tệp | Công dụng |
|---|---|
| `app-data.zip` | Mã nguồn web của bạn + biểu tượng (muốn cập nhật nội dung thì thay tệp này) |
| `package.json`, `capacitor.config.json` | Thông tin ứng dụng (tên, mã gói, phiên bản) |
| `prepare.js` | Giải nén `app-data.zip` khi build |
| `main.js` | Vỏ Electron cho bản Windows |
| `.github/workflows/build.yml` | Kịch bản build tự động |

## Cách làm (khoảng 10 phút)

1. Đăng nhập GitHub, bấm **New repository**, đặt tên, chọn **Public** (để học sinh tải được; xem lưu ý bên dưới), bấm **Create repository**.
2. Bấm **uploading an existing file**, kéo thả `app-data.zip`, `package.json`, `capacitor.config.json`, `prepare.js`, `main.js` vào, rồi bấm **Commit changes**.
3. Tạo tệp kịch bản: bấm **Add file → Create new file**, ở ô tên gõ đúng `.github/workflows/build.yml` (gõ dấu `/` GitHub tự tạo thư mục), mở tệp `build.yml` trong gói bằng Notepad, chép toàn bộ nội dung dán vào, bấm **Commit changes**. (Nếu kéo thả được cả thư mục `.github` thì không cần bước này.)
4. Vào thẻ **Actions**: build tự chạy sau khi bạn commit tệp ở bước 3 (hoặc chọn **Đóng gói ứng dụng → Run workflow**). Chờ khoảng 10–20 phút.
5. Xong, vào trang chính của repo, cột bên phải mục **Releases**, mở bản mới nhất: các tệp `.apk`, `.exe`, `.ipa` nằm trong mục **Assets**.

## Cài đặt trên thiết bị

- **Android (.apk):** chép tệp vào điện thoại, mở lên và cho phép "Cài đặt từ nguồn không xác định" khi máy hỏi.

## Cập nhật nội dung ứng dụng

Dùng công cụ tạo lại `app-data.zip` (nút "Chỉ tạo app-data.zip"), vào repo bấm **Add file → Upload files** để tải tệp mới lên (ghi đè tệp cũ). Build tự chạy lại và tạo bản phát hành mới.

## Lưu ý quan trọng

- **Repo Private** vẫn build được nhưng chỉ người có quyền truy cập repo mới tải được tệp. Gói miễn phí của GitHub giới hạn số phút build mỗi tháng, và phút chạy macOS (iOS) bị tính gấp 10 lần.
- Tên tệp trong ứng dụng **phân biệt chữ hoa/thường** trên Android (`Data.json` khác `data.json`). Hãy gõ đúng tên khi gọi tệp trong mã nguồn.
- Ứng dụng dùng thư viện từ internet (CDN) cần có mạng khi chạy. Muốn chạy offline, hãy tải thư viện về, để cùng thư mục mã nguồn và sửa đường dẫn.
- Trên Android, các nút tải tệp kiểu `<a download>` (xuất Excel, Word...) không hoạt động trong ứng dụng đóng gói vì WebView không hỗ trợ; bản Windows thì hoạt động bình thường.
- Bản APK được ký bằng khóa debug và khóa này **đổi mỗi lần build**, nên muốn cập nhật phải gỡ bản cũ rồi cài bản mới. Muốn đưa lên Google Play cần ký bằng khóa riêng.
