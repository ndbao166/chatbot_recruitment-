#!/usr/bin/env python3
"""
Script để chuyển đổi Google Sheets credentials từ file JSON sang format .env
Sử dụng: python convert_json_to_env.py [path_to_json_file]
"""

import json
import sys
import os


def convert_json_to_env(json_file_path):
    """Đọc file JSON và xuất ra format .env"""
    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print("# Google Sheets Credentials - Generated from JSON")
        print("# Copy các dòng dưới đây vào file .env của bạn\n")
        print("# ============================================")
        
        # Map từ JSON keys sang ENV variable names
        mapping = {
            "type": "GOOGLE_SHEETS_CREDENTIALS_TYPE",
            "project_id": "GOOGLE_SHEETS_CREDENTIALS_PROJECT_ID",
            "private_key_id": "GOOGLE_SHEETS_CREDENTIALS_PRIVATE_KEY_ID",
            "private_key": "GOOGLE_SHEETS_CREDENTIALS_PRIVATE_KEY",
            "client_email": "GOOGLE_SHEETS_CREDENTIALS_CLIENT_EMAIL",
            "client_id": "GOOGLE_SHEETS_CREDENTIALS_CLIENT_ID",
            "auth_uri": "GOOGLE_SHEETS_CREDENTIALS_AUTH_URI",
            "token_uri": "GOOGLE_SHEETS_CREDENTIALS_TOKEN_URI",
            "auth_provider_x509_cert_url": "GOOGLE_SHEETS_CREDENTIALS_AUTH_PROVIDER_X509_CERT_URL",
            "client_x509_cert_url": "GOOGLE_SHEETS_CREDENTIALS_CLIENT_X509_CERT_URL",
        }
        
        for json_key, env_key in mapping.items():
            if json_key in data:
                value = data[json_key]
                
                # Xử lý private_key đặc biệt (cần giữ \n và đặt trong dấu ngoặc kép)
                if json_key == "private_key":
                    # Đảm bảo giữ nguyên \n trong private key
                    print(f'{env_key}="{value}"')
                else:
                    # Các giá trị khác
                    print(f'{env_key}={value}')
        
        # Thêm universe_domain nếu có, nếu không thì dùng mặc định
        if "universe_domain" in data:
            print(f'GOOGLE_SHEETS_CREDENTIALS_UNIVERSE_DOMAIN={data["universe_domain"]}')
        else:
            print('GOOGLE_SHEETS_CREDENTIALS_UNIVERSE_DOMAIN=googleapis.com')
        
        print("\n# ============================================")
        print("# Các biến cấu hình khác (cần điền thủ công)")
        print("# ============================================")
        print("GOOGLE_SHEETS_SPREADSHEET_ID=your-spreadsheet-id-here")
        print("KNOWLEDGE_BASE_SHEET_ID=Knowledge")
        print("JOB_SHEET_ID=Jobs")
        print("INFO_SHEET_ID=UserInfo")
        
        print("\n# ============================================")
        print("# HƯỚNG DẪN:")
        print("# 1. Copy toàn bộ output trên vào file .env")
        print("# 2. Thay 'your-spreadsheet-id-here' bằng Spreadsheet ID thật")
        print("# 3. Cài đặt python-dotenv: pip install python-dotenv")
        print("# 4. Load .env trong code: from dotenv import load_dotenv; load_dotenv()")
        print("# 5. Test thử xem có hoạt động không")
        print("# ============================================\n")
        
        return True
        
    except FileNotFoundError:
        print(f"❌ Lỗi: Không tìm thấy file {json_file_path}")
        return False
    except json.JSONDecodeError:
        print(f"❌ Lỗi: File {json_file_path} không phải là JSON hợp lệ")
        return False
    except Exception as e:
        print(f"❌ Lỗi: {str(e)}")
        return False


def main():
    """Main function"""
    
    # Mặc định là file credentials trong thư mục data/
    default_file = "data/freelancer-476916-1703e2c93b82.json"
    
    # Nếu có argument thì dùng argument, không thì dùng default
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
    else:
        json_file = default_file
    
    print(f"\n📄 Đang chuyển đổi file: {json_file}\n")
    
    if not os.path.exists(json_file):
        print(f"❌ File không tồn tại: {json_file}")
        print(f"\nCách sử dụng:")
        print(f"  python {sys.argv[0]} [path_to_json_file]")
        print(f"\nVí dụ:")
        print(f"  python {sys.argv[0]} data/your-credentials.json")
        sys.exit(1)
    
    success = convert_json_to_env(json_file)
    
    if success:
        print("✅ Chuyển đổi thành công!\n")
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()

