#!/usr/bin/env python
"""
环境检查脚本
检查生产环境配置是否正确
"""
import os
import sys
import django
from django.conf import settings

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'unieat.settings')
django.setup()

def check_database():
    """检查数据库连接"""
    try:
        from django.db import connection
        connection.ensure_connection()
        print("✅ 数据库连接正常")
        return True
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False

def check_static_files():
    """检查静态文件配置"""
    static_root = settings.STATIC_ROOT
    if os.path.exists(static_root):
        print(f"✅ 静态文件目录存在: {static_root}")
        return True
    else:
        print(f"❌ 静态文件目录不存在: {static_root}")
        return False

def check_media_files():
    """检查媒体文件配置"""
    media_root = settings.MEDIA_ROOT
    if os.path.exists(media_root):
        print(f"✅ 媒体文件目录存在: {media_root}")
        return True
    else:
        print(f"❌ 媒体文件目录不存在: {media_root}")
        return False

def check_oss_config():
    """检查阿里云OSS配置"""
    if hasattr(settings, 'OSS_ACCESS_KEY_ID') and settings.OSS_ACCESS_KEY_ID:
        print("✅ 阿里云OSS配置已设置")
        return True
    else:
        print("⚠️ 阿里云OSS配置未设置，将使用本地存储")
        return True

def check_environment_variables():
    """检查关键环境变量"""
    required_vars = ['SECRET_KEY', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
    missing_vars = []
    
    for var in required_vars:
        if not getattr(settings, var, None):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ 缺少关键环境变量: {', '.join(missing_vars)}")
        return False
    else:
        print("✅ 关键环境变量配置完整")
        return True

def check_log_directories():
    """检查日志目录"""
    log_path = getattr(settings, 'LOG_FILE_PATH', None)
    if log_path and os.path.exists(log_path):
        print(f"✅ 日志目录存在: {log_path}")
        return True
    else:
        print(f"❌ 日志目录不存在: {log_path}")
        return False

def main():
    """主检查函数"""
    print("🔍 开始环境检查...")
    print("=" * 50)
    
    checks = [
        check_environment_variables,
        check_database,
        check_static_files,
        check_media_files,
        check_oss_config,
        check_log_directories,
    ]
    
    results = []
    for check in checks:
        try:
            result = check()
            results.append(result)
        except Exception as e:
            print(f"❌ 检查失败: {e}")
            results.append(False)
        print("-" * 30)
    
    # 汇总结果
    passed = sum(results)
    total = len(results)
    
    print(f"📊 检查结果: {passed}/{total} 项通过")
    
    if passed == total:
        print("🎉 环境检查全部通过！")
        sys.exit(0)
    else:
        print("⚠️ 环境检查发现问题，请修复后重试")
        sys.exit(1)

if __name__ == "__main__":
    main()
