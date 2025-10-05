import os
import sys
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'unieat.settings')
sys.path.append(os.path.join(os.path.dirname(__file__), 'unieat'))

# 初始化Django
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    stall_id = input("请输入要删除的档口ID: ")
    
    # 查看要删除的数据
    cursor.execute("SELECT COUNT(*) FROM unieat_v1_usermealrecord WHERE stall_id = %s", [stall_id])
    record_count = cursor.fetchone()[0]
    print(f"找到 {record_count} 条相关的UserMealRecord记录")
    
    confirm = input(f"确认删除档口ID {stall_id} 及其所有相关用餐记录吗？(y/N): ")
    if confirm.lower() == 'y':
        # 删除相关的UserMealRecord记录
        cursor.execute("DELETE FROM unieat_v1_usermealrecord WHERE stall_id = %s", [stall_id])
        deleted_count = cursor.rowcount
        print(f"删除了 {deleted_count} 条UserMealRecord记录")
        
        # 删除档口
        cursor.execute("DELETE FROM unieat_v1_stall WHERE id = %s", [stall_id])
        if cursor.rowcount > 0:
            print("成功删除档口")
        else:
            print("未找到要删除的档口")
    else:
        print("取消删除")