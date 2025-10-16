#!/usr/bin/env python
"""
数据迁移脚本
用于将本地开发环境的数据迁移到生产环境
"""
import os
import sys
import django
import json
from datetime import datetime

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'unieat.settings')
django.setup()

from django.core.management import call_command
from django.core.management.base import CommandError

def export_data():
    """导出数据到fixture文件"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fixture_file = f"fixtures/unieat_data_{timestamp}.json"
    
    print(f"📦 开始导出数据到: {fixture_file}")
    
    # 确保fixtures目录存在
    os.makedirs("fixtures", exist_ok=True)
    
    try:
        # 导出所有数据
        with open(fixture_file, 'w', encoding='utf-8') as f:
            call_command('dumpdata', stdout=f, indent=2)
        
        print(f"✅ 数据导出成功: {fixture_file}")
        return fixture_file
    except CommandError as e:
        print(f"❌ 数据导出失败: {e}")
        return None

def import_data(fixture_file):
    """从fixture文件导入数据"""
    if not os.path.exists(fixture_file):
        print(f"❌ Fixture文件不存在: {fixture_file}")
        return False
    
    print(f"📥 开始导入数据从: {fixture_file}")
    
    try:
        call_command('loaddata', fixture_file)
        print(f"✅ 数据导入成功: {fixture_file}")
        return True
    except CommandError as e:
        print(f"❌ 数据导入失败: {e}")
        return False

def migrate_database():
    """执行数据库迁移"""
    print("🗄️ 执行数据库迁移...")
    
    try:
        call_command('migrate', verbosity=1)
        print("✅ 数据库迁移成功")
        return True
    except CommandError as e:
        print(f"❌ 数据库迁移失败: {e}")
        return False

def create_superuser():
    """创建超级用户"""
    print("👤 检查超级用户...")
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    if not User.objects.filter(is_superuser=True).exists():
        print("⚠️ 未找到超级用户，请手动创建:")
        print("python manage.py createsuperuser")
        return False
    else:
        print("✅ 超级用户已存在")
        return True

def check_data_integrity():
    """检查数据完整性"""
    print("🔍 检查数据完整性...")
    
    from unieat_v1.models import Canteen, Stall, Dish
    
    # 检查基础数据
    canteen_count = Canteen.objects.count()
    stall_count = Stall.objects.count()
    dish_count = Dish.objects.count()
    
    print(f"📊 数据统计:")
    print(f"   食堂数量: {canteen_count}")
    print(f"   档口数量: {stall_count}")
    print(f"   菜品数量: {dish_count}")
    
    if canteen_count == 0:
        print("⚠️ 警告: 没有食堂数据")
        return False
    
    if stall_count == 0:
        print("⚠️ 警告: 没有档口数据")
        return False
    
    if dish_count == 0:
        print("⚠️ 警告: 没有菜品数据")
        return False
    
    print("✅ 数据完整性检查通过")
    return True

def main():
    """主函数"""
    if len(sys.argv) > 1:
        action = sys.argv[1]
        
        if action == "export":
            export_data()
        elif action == "import":
            if len(sys.argv) > 2:
                fixture_file = sys.argv[2]
                import_data(fixture_file)
            else:
                print("❌ 请指定fixture文件路径")
                print("使用方法: python migrate_data.py import fixtures/unieat_data_20240101_120000.json")
        elif action == "migrate":
            migrate_database()
        elif action == "check":
            check_data_integrity()
        elif action == "full":
            # 完整迁移流程
            print("🚀 开始完整数据迁移流程...")
            
            # 1. 数据库迁移
            if not migrate_database():
                return
            
            # 2. 检查数据完整性
            if not check_data_integrity():
                print("⚠️ 数据不完整，请先导入数据")
                return
            
            # 3. 创建超级用户
            create_superuser()
            
            print("🎉 完整数据迁移流程完成！")
        else:
            print("❌ 未知操作")
            print_help()
    else:
        print_help()

def print_help():
    """打印帮助信息"""
    print("📋 数据迁移工具")
    print("使用方法:")
    print("  python migrate_data.py export          - 导出数据")
    print("  python migrate_data.py import <file>   - 导入数据")
    print("  python migrate_data.py migrate         - 执行数据库迁移")
    print("  python migrate_data.py check           - 检查数据完整性")
    print("  python migrate_data.py full            - 完整迁移流程")
    print("")
    print("示例:")
    print("  python migrate_data.py export")
    print("  python migrate_data.py import fixtures/unieat_data_20240101_120000.json")

if __name__ == "__main__":
    main()
