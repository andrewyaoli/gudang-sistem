from datetime import datetime

class User:
    def __init__(self, username, password, role):
        self.username = username
        self.password = password
        self.role = role  # 'admin' 或 'user'

class UserSystem:
    def __init__(self):
        self.users = {
            'admin': User('admin', 'admin123', 'admin'),  # 默认管理员账户
            'user1': User('user1', 'user123', 'user')     # 默认普通用户账户
        }
    
    def login(self, username, password):
        if username in self.users and self.users[username].password == password:
            return self.users[username]
        return None
    
    def add_user(self, username, password, role):
        if username in self.users:
            print("用户名已存在！")
            return False
        self.users[username] = User(username, password, role)
        print(f"用户 {username} 创建成功！")
        return True

class Product:
    def __init__(self, product_id, name, quantity, price):
        self.product_id = product_id
        self.name = name
        self.specification = None  # 添加规格字段
        self.quantity = quantity
        self.price = price

class StockRecord:
    def __init__(self, product_id, operation_type, quantity, operator, timestamp=None):
        self.product_id = product_id
        self.operation_type = operation_type  # 'in'入库, 'out'出库, 'adjust'调整
        self.destination = None  # 添加出库目的地
        self.quantity = quantity
        self.operator = operator
        self.timestamp = timestamp or datetime.now()

class WarehouseSystem:
    def __init__(self):
        self.products = {}
        self.user_system = UserSystem()
        self.current_user = None
        self.stock_records = []  # 添加库存记录列表

    def login(self, username, password):
        user = self.user_system.login(username, password)
        if user:
            self.current_user = user
            print(f"\n欢迎, {username}! 角色: {user.role}")
            return True
        print("用户名或密码错误！")
        return False

    def check_admin_permission(self):
        return self.current_user and self.current_user.role == 'admin'

    def add_product(self, product_id, name, quantity, price):
        # 验证输入数据
        try:
            quantity = int(quantity)
            price = float(price)
            if quantity < 0 or price < 0:
                raise ValueError("数量和价格不能为负数")
        except ValueError as e:
            print(f"输入数据无效: {str(e)}")
            return False

        # 检查商品ID是否已存在
        if product_id in self.products:
            print(f"商品ID {product_id} 已存在！")
            return False

        # 检查商品名称是否为空
        if not name or name.strip() == "":
            print("商品名称不能为空！")
            return False

        # 创建新商品
        try:
            self.products[product_id] = Product(product_id, name, quantity, price)
            print(f"商品 {name} 添加成功！")
            return True
        except Exception as e:
            print(f"添加商品时发生错误: {str(e)}")
            return False

    def remove_product(self, product_id):
        if not self.check_admin_permission():
            print("权限不足！只有管理员可以删除商品。")
            return False
        if product_id in self.products:
            product = self.products.pop(product_id)
            print(f"商品 {product.name} 已删除！")
            return True
        print(f"商品ID {product_id} 不存在！")
        return False

    def update_quantity(self, product_id, quantity):
        if not self.check_admin_permission():
            print("权限不足！只有管理员可以更新库存。")
            return False
        try:
            quantity = int(quantity)
            if quantity < 0:
                raise ValueError("数量不能为负数")
        except ValueError as e:
            print(f"输入数据无效: {str(e)}")
            return False

        if product_id in self.products:
            self.products[product_id].quantity = quantity
            print(f"商品 {self.products[product_id].name} 库存已更新为 {quantity}")
            return True
        print(f"商品ID {product_id} 不存在！")
        return False

    def get_product_info(self, product_id):
        if product_id in self.products:
            product = self.products[product_id]
            return {
                "商品ID": product.product_id,
                "名称": product.name,
                "库存": product.quantity,
                "价格": product.price
            }
        return None

    def display_all_products(self):
        if not self.products:
            print("仓库为空！")
            return
        print("\n当前库存商品列表：")
        print("商品ID\t名称\t\t库存\t价格")
        print("-" * 40)
        for product in self.products.values():
            print(f"{product.product_id}\t{product.name}\t\t{product.quantity}\t{product.price}")

    def get_total_products(self):
        return len(self.products)

    def get_total_quantity(self):
        return sum(product.quantity for product in self.products.values())

    def get_total_value(self):
        return sum(product.quantity * product.price for product in self.products.values())

    def get_low_stock_count(self, threshold=10):
        return len([p for p in self.products.values() if p.quantity < threshold])

    def stock_in(self, product_id, quantity):
        """入库操作"""
        if not self.check_admin_permission():
            print("权限不足！只有管理员可以执行入库操作。")
            return False
            
        try:
            quantity = int(quantity)
            if quantity <= 0:
                raise ValueError("入库数量必须为正数")
                
            if product_id not in self.products:
                print(f"商品ID {product_id} 不存在！")
                return False
                
            product = self.products[product_id]
            product.quantity += quantity
            
            # 记录入库操作
            record = StockRecord(
                product_id=product_id,
                operation_type='in',
                quantity=quantity,
                operator=self.current_user.username
            )
            self.stock_records.append(record)
            
            print(f"入库成功！商品 {product.name} 当前库存: {product.quantity}")
            return True
            
        except ValueError as e:
            print(f"输入数据无效: {str(e)}")
            return False

    def stock_out(self, product_id, quantity):
        """出库操作"""
        if not self.check_admin_permission():
            print("权限不足！只有管理员可以执行出库操作。")
            return False
            
        try:
            quantity = int(quantity)
            if quantity <= 0:
                raise ValueError("出库数量必须为正数")
                
            if product_id not in self.products:
                print(f"商品ID {product_id} 不存在！")
                return False
                
            product = self.products[product_id]
            if product.quantity < quantity:
                print(f"库存不足！当前库存: {product.quantity}")
                return False
                
            product.quantity -= quantity
            
            # 记录出库操作
            record = StockRecord(
                product_id=product_id,
                operation_type='out',
                quantity=quantity,
                operator=self.current_user.username
            )
            self.stock_records.append(record)
            
            print(f"出库成功！商品 {product.name} 当前库存: {product.quantity}")
            return True
            
        except ValueError as e:
            print(f"输入数据无效: {str(e)}")
            return False

    def get_stock_records(self, product_id=None, start_date=None, end_date=None):
        """获取库存变动记录"""
        records = self.stock_records
        
        if product_id:
            records = [r for r in records if r.product_id == product_id]
            
        if start_date:
            records = [r for r in records if r.timestamp >= start_date]
            
        if end_date:
            records = [r for r in records if r.timestamp <= end_date]
            
        return records

    def display_stock_records(self, product_id=None):
        """显示库存变动记录"""
        records = self.get_stock_records(product_id)
        
        if not records:
            print("没有找到库存记录！")
            return
            
        print("\n库存变动记录：")
        print("时间\t\t\t商品ID\t\t操作类型\t数量\t操作员")
        print("-" * 70)
        
        for record in records:
            product = self.products.get(record.product_id)
            product_name = product.name if product else "未知商品"
            operation_type_map = {
                'in': '入库',
                'out': '出库',
                'adjust': '调整'
            }
            print(f"{record.timestamp:%Y-%m-%d %H:%M:%S}\t"
                  f"{record.product_id}\t"
                  f"{operation_type_map.get(record.operation_type)}\t\t"
                  f"{record.quantity}\t"
                  f"{record.operator}")

    def check_low_stock(self, threshold=10):
        """检查低库存商品"""
        low_stock_products = [p for p in self.products.values() if p.quantity < threshold]
        
        if not low_stock_products:
            print("没有低库存商品！")
            return
            
        print("\n低库存商品列表（库存 < 10）：")
        print("商品ID\t名称\t\t当前库存\t预警阈值")
        print("-" * 50)
        
        for product in low_stock_products:
            print(f"{product.product_id}\t"
                  f"{product.name}\t\t"
                  f"{product.quantity}\t"
                  f"{threshold}")

def main():
    warehouse = WarehouseSystem()
    
    while True:
        print("\n=== 仓库管理系统登录 ===")
        username = input("用户名: ")
        password = input("密码: ")
        
        if warehouse.login(username, password):
            break
        print("登录失败，请重试！")
    
    while True:
        print("\n=== 仓库管理系统 ===")
        print("1. 添加商品 (仅管理员)")
        print("2. 删除商品 (仅管理员)")
        print("3. 库存管理")
        print("4. 查询商品")
        print("5. 显示所有商品")
        print("6. 库存记录")
        print("7. 库存预警")
        print("0. 退出系统")
        
        choice = input("\n请选择操作 (0-7): ")
        
        try:
            if choice == "1":
                product_id = input("请输入商品ID: ")
                name = input("请输入商品名称: ")
                quantity = input("请输入库存数量: ")
                price = input("请输入商品价格: ")
                warehouse.add_product(product_id, name, quantity, price)
                
            elif choice == "2":
                product_id = input("请输入要删除的商品ID: ")
                warehouse.remove_product(product_id)
                
            elif choice == "3":
                print("\n=== 库存管理 ===")
                print("1. 入库")
                print("2. 出库")
                print("3. 库存调整")
                print("0. 返回主菜单")
                
                stock_choice = input("\n请选择操作 (0-3): ")
                
                if stock_choice == "1":
                    product_id = input("请输入商品ID: ")
                    quantity = input("请输入入库数量: ")
                    warehouse.stock_in(product_id, quantity)
                    
                elif stock_choice == "2":
                    product_id = input("请输入商品ID: ")
                    quantity = input("请输入出库数量: ")
                    warehouse.stock_out(product_id, quantity)
                    
                elif stock_choice == "3":
                    product_id = input("请输入商品ID: ")
                    quantity = input("请输入新的库存数量: ")
                    warehouse.update_quantity(product_id, quantity)
                    
            elif choice == "4":
                product_id = input("请输入商品ID: ")
                info = warehouse.get_product_info(product_id)
                if info:
                    print("\n商品信息：")
                    for key, value in info.items():
                        print(f"{key}: {value}")
                else:
                    print(f"商品ID {product_id} 不存在！")
                    
            elif choice == "5":
                warehouse.display_all_products()
                
            elif choice == "6":
                product_id = input("请输入商品ID（直接回车显示所有记录）: ")
                warehouse.display_stock_records(product_id if product_id else None)
                
            elif choice == "7":
                warehouse.check_low_stock()
                
            elif choice == "0":
                print("感谢使用！再见！")
                break
                
            else:
                print("无效的选择，请重试！")
                
        except ValueError:
            print("输入格式错误，请重试！")

if __name__ == "__main__":
    main() 

# 将系统中的中文提示信息改为印尼语
messages = {
    # 库存管理相关
    "库存管理": "Manajemen Stok",
    "入库": "Barang Masuk",
    "出库": "Barang Keluar",
    "库存调整": "Penyesuaian Stok",
    "库存不足": "Stok Tidak Cukup",
    "当前库存": "Stok Saat Ini",
    
    # 商品信息相关
    "商品ID": "Kode Produk",
    "商品名称": "Nama Produk",
    "规格": "Spesifikasi",
    "数量": "Jumlah",
    "价格": "Harga",
    "供应商": "Pemasok",
    
    # 操作相关
    "操作类型": "Jenis Operasi",
    "操作时间": "Waktu Operasi",
    "操作员": "Operator",
    "确认": "Konfirmasi",
    "取消": "Batal",
    
    # 提示信息
    "操作成功": "Operasi Berhasil",
    "操作失败": "Operasi Gagal",
    "权限不足": "Hak Akses Tidak Cukup",
    "输入无效": "Input Tidak Valid"
} 