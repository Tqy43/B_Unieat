#!/usr/bin/env python
"""
在生产环境创建 Django Admin 用户
使用方法：
1. 上传此文件到生产服务器
2. 在项目根目录执行：python deploy/scripts/create_admin_user.py
"""
import os
import sys
import django

# 添加项目路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'unieat.settings')
django.setup()

from django.contrib.auth.models import User

# 用户配置
USERNAME = 'Super'
PASSWORD = 'Super1234'
EMAIL = 'super@unieat.top'

def main():
    print("=" * 60)
    print("创建 Django Admin 超级用户")
    print("=" * 60)
    
    # 检查是否已有该用户
    try:
        user = User.objects.get(username=USERNAME)
        print(f"\n用户 '{USERNAME}' 已存在，正在更新...")
        user.set_password(PASSWORD)
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        if not user.email:
            user.email = EMAIL
        user.save()
        print("[OK] 用户已更新")
    except User.DoesNotExist:
        print(f"\n创建新用户 '{USERNAME}'...")
        user = User.objects.create_superuser(
            username=USERNAME,
            email=EMAIL,
            password=PASSWORD
        )
        print("[OK] 用户已创建")
    
    # 删除其他超级用户
    print(f"\n删除其他超级用户...")
    other_superusers = User.objects.filter(is_superuser=True).exclude(username=USERNAME)
    count = other_superusers.count()
    
    if count > 0:
        print(f"找到 {count} 个其他超级用户:")
        for u in other_superusers:
            print(f"  - {u.username} (ID: {u.id})")
        
        confirm = input(f"\n确认删除这 {count} 个用户? (yes/no): ")
        if confirm.lower() == 'yes':
            deleted = other_superusers.delete()[0]
            print(f"[OK] 已删除 {deleted} 个用户")
        else:
            print("[SKIP] 已取消删除")
    else:
        print("[OK] 没有其他超级用户需要删除")
    
    # 显示结果
    print(f"\n" + "=" * 60)
    print("最终结果:")
    print("=" * 60)
    all_superusers = User.objects.filter(is_superuser=True)
    print(f"超级用户数量: {all_superusers.count()}")
    for u in all_superusers:
        print(f"  - {u.username} (staff={u.is_staff}, active={u.is_active})")
    
    print(f"\n" + "=" * 60)
    print("登录信息:")
    print("=" * 60)
    print(f"用户名: {USERNAME}")
    print(f"密码: {PASSWORD}")
    print(f"访问地址: https://unieat.top/admin/")
    print("=" * 60)

if __name__ == '__main__':
    main()













