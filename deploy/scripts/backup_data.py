#!/usr/bin/env python
"""
数据备份脚本
使用Django的dumpdata命令备份数据
"""
import os
import sys
import django
from datetime import datetime

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'unieat.settings')
django.setup()

def backup_database():
    """备份数据库数据"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"fixtures/backup_{timestamp}.json"
    
    print(f"📦 开始备份数据到: {backup_filename}")
    
    # 创建fixtures目录
    os.makedirs("fixtures", exist_ok=True)
    
    # 执行备份命令
    cmd = f"python manage.py dumpdata > {backup_filename}"
    result = os.system(cmd)
    
    if result == 0:
        print(f"✅ 数据备份成功: {backup_filename}")
        return backup_filename
    else:
        print("❌ 数据备份失败")
        return None

def restore_database(backup_file):
    """恢复数据库数据"""
    if not os.path.exists(backup_file):
        print(f"❌ 备份文件不存在: {backup_file}")
        return False
    
    print(f"📥 开始恢复数据从: {backup_file}")
    
    # 执行恢复命令
    cmd = f"python manage.py loaddata {backup_file}"
    result = os.system(cmd)
    
    if result == 0:
        print(f"✅ 数据恢复成功: {backup_file}")
        return True
    else:
        print("❌ 数据恢复失败")
        return False

def main():
    """主函数"""
    if len(sys.argv) > 1:
        action = sys.argv[1]
        if action == "backup":
            backup_database()
        elif action == "restore":
            if len(sys.argv) > 2:
                backup_file = sys.argv[2]
                restore_database(backup_file)
            else:
                print("❌ 请指定备份文件路径")
                print("使用方法: python backup_data.py restore fixtures/backup_20240101_120000.json")
        else:
            print("❌ 未知操作，支持的操作: backup, restore")
    else:
        print("📋 数据备份/恢复工具")
        print("使用方法:")
        print("  备份: python backup_data.py backup")
        print("  恢复: python backup_data.py restore <备份文件路径>")

if __name__ == "__main__":
    main()
