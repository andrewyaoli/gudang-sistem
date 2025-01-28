from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify
from flask_sqlalchemy import SQLAlchemy
from models import db, User, Product, StockRecord
import os
from datetime import datetime, timedelta
from sqlalchemy import func
import io
import xlsxwriter
import sqlalchemy

app = Flask(__name__)

# 基本配置
app.secret_key = 'your_secret_key_here'
basedir = os.path.abspath(os.path.dirname(__file__))

# 数据库配置
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'warehouse.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化数据库
db.init_app(app)

# 创建数据库表和默认用户
with app.app_context():
    db.create_all()
    # 检查是否需要创建默认管理员账户
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            flash('Login Berhasil!', 'success')
            return redirect(url_for('dashboard'))
            
        flash('Nama Pengguna atau Kata Sandi Salah!', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    products = Product.query.all()
    total_quantity = sum(p.quantity for p in products)
    total_value = sum(p.quantity * p.price for p in products)
    low_stock_count = len([p for p in products if p.quantity < p.min_quantity])
    
    return render_template('dashboard.html',
                         products=products,
                         total_products=len(products),
                         total_quantity=total_quantity,
                         total_value=total_value,
                         low_stock_count=low_stock_count,
                         is_admin=session.get('role') == 'admin',
                         session=session)

@app.route('/add_product', methods=['POST'])
def add_product():
    if session.get('role') != 'admin':
        flash('Hak Akses Tidak Cukup!', 'error')
        return redirect(url_for('products'))
    
    try:
        # 自动生成商品ID
        product_id = get_next_product_id()
        product_name = request.form['name']  # 获取商品名称

        product = Product(
            product_id=product_id,
            name=product_name,
            specification=request.form['specification'],
            quantity=0,
            min_quantity=int(request.form['min_quantity']),
            price=float(request.form['price'])
        )
        
        db.session.add(product)
        db.session.commit()
        
        flash(f'Produk {product_name} Berhasil Ditambahkan!', 'success')  # 显示商品名称
    except Exception as e:
        db.session.rollback()
        if isinstance(e, sqlalchemy.exc.IntegrityError):
            flash('Kode Produk Sudah Ada!', 'error')
        else:
            flash(f'Gagal: {str(e)}', 'error')
    
    return redirect(url_for('products'))

@app.route('/remove_product/<product_id>')
def remove_product(product_id):
    if session.get('role') != 'admin':
        flash('权限不足！', 'error')
        return redirect(url_for('products'))
    
    try:
        product = Product.query.filter_by(product_id=product_id).first()
        if product:
            # 先删除关联的库存记录
            StockRecord.query.filter_by(product_id=product_id).delete()
            # 再删除商品
            db.session.delete(product)
            db.session.commit()
            flash('Produk Berhasil Dihapus!', 'success')
        else:
            flash('Produk Tidak Ditemukan!', 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'Gagal: {str(e)}', 'error')
    
    return redirect(url_for('products'))

@app.route('/update_quantity', methods=['POST'])
def update_quantity():
    if session.get('role') != 'admin':
        flash('权限不足！', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        product_id = request.form['product_id']
        quantity = int(request.form['quantity'])
        
        product = Product.query.filter_by(product_id=product_id).first()
        if product:
            product.quantity = quantity
            db.session.commit()
            flash('库存更新成功！', 'success')
        else:
            flash('商品不存在！', 'error')
    except ValueError:
        flash('输入数据格式错误！', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/stock_in', methods=['POST'])
def stock_in():
    if 'user_id' not in session:
        flash('Hak Akses Tidak Cukup!', 'error')  # 权限不足
        return redirect(url_for('inventory'))
    
    try:
        product_id = request.form['product_id']
        quantity = int(request.form['quantity'])
        supplier = request.form['supplier']
        
        if quantity <= 0:
            raise ValueError("Jumlah harus positif")  # 数量必须为正数
        
        product = Product.query.filter_by(product_id=product_id).first()
        if not product:
            flash('Produk tidak ditemukan!', 'error')  # 商品不存在
            return redirect(url_for('inventory'))
        
        product.quantity += quantity
        product.supplier = supplier
        
        record = StockRecord(
            product_id=product_id,
            operation_type='in',
            quantity=quantity,
            supplier=supplier,
            operator_id=session['user_id']
        )
        
        db.session.add(record)
        db.session.commit()
        
        flash('Barang Masuk Berhasil!', 'success')  # 入库成功
    except Exception as e:
        db.session.rollback()
        flash(f'Gagal: {str(e)}', 'error')  # 入库失败
    
    return redirect(url_for('inventory'))

@app.route('/stock_out', methods=['POST'])
def stock_out():
    if 'user_id' not in session:
        flash('Hak Akses Tidak Cukup!', 'error')  # 权限不足
        return redirect(url_for('inventory'))
    
    try:
        product_id = request.form['product_id']
        quantity = int(request.form['quantity'])
        destination = request.form['destination']
        
        if quantity <= 0:
            raise ValueError("Jumlah harus positif")  # 数量必须为正数
        
        product = Product.query.filter_by(product_id=product_id).first()
        if not product:
            flash('Produk tidak ditemukan!', 'error')  # 商品不存在
            return redirect(url_for('inventory'))
            
        if product.quantity < quantity:
            flash(f'Stok Tidak Cukup! Stok Saat Ini: {product.quantity}', 'error')  # 库存不足
            return redirect(url_for('inventory'))
        
        product.quantity -= quantity
        
        record = StockRecord(
            product_id=product_id,
            operation_type='out',
            destination=destination,
            quantity=quantity,
            operator_id=session['user_id']
        )
        
        db.session.add(record)
        db.session.commit()
        
        flash('Barang Keluar Berhasil!', 'success')  # 出库成功
    except Exception as e:
        db.session.rollback()
        flash(f'Gagal: {str(e)}', 'error')  # 出库失败
    
    return redirect(url_for('inventory'))

@app.route('/stock_records')
def stock_records():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    product_id = request.args.get('product_id')
    query = StockRecord.query.order_by(StockRecord.timestamp.desc())
    
    if product_id:
        query = query.filter_by(product_id=product_id)
    
    records = query.all()
    products = {p.product_id: p for p in Product.query.all()}
    
    return render_template('stock_records.html',
                         records=records,
                         products=products,
                         is_admin=session.get('role') == 'admin',
                         session=session)

@app.route('/low_stock')
def low_stock():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    threshold = 10
    products = Product.query.filter(Product.quantity < threshold).all()
    
    return render_template('low_stock.html',
                         products=products,
                         threshold=threshold,
                         is_admin=session.get('role') == 'admin',
                         session=session)

@app.route('/inventory')
def inventory():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # 只允许 admin 和 user 角色访问
    if session.get('role') not in ['admin', 'user']:
        flash('Hak Akses Tidak Cukup!', 'error')
        return redirect(url_for('dashboard'))
    
    # 获取最近的库存记录
    records = StockRecord.query.order_by(StockRecord.timestamp.desc()).limit(10).all()
    products = {p.product_id: p for p in Product.query.all()}
    
    # 翻译提示消息
    messages = {
        'success': 'Berhasil',
        'error': 'Gagal',
        'stock_in': 'Barang Masuk',
        'stock_out': 'Barang Keluar',
        'product_id': 'Kode Produk',
        'product_name': 'Nama Produk',
        'quantity': 'Jumlah',
        'supplier': 'Pemasok',
        'destination': 'Tujuan',
        'operation_time': 'Waktu Operasi',
        'operator': 'Operator',
        'operation_type': 'Jenis Operasi',
        'current_stock': 'Stok Saat Ini',
        'submit': 'Konfirmasi',
        'cancel': 'Batal',
        'search': 'Cari',
        'no_records': 'Tidak Ada Catatan',
        'stock_records': 'Catatan Stok',
        'recent_operations': 'Operasi Terbaru'
    }
    
    return render_template('inventory.html',
                         records=records,
                         products=products,
                         messages=messages,  # 传递翻译后的消息
                         is_admin=session.get('role') == 'admin',
                         session=session)

@app.route('/products')
def products():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # 允许 admin、user 和 viewer 角色访问
    if session.get('role') not in ['admin', 'user', 'viewer']:
        flash('Hak Akses Tidak Cukup!', 'error')
        return redirect(url_for('dashboard'))
    
    products = Product.query.order_by(Product.product_id.asc()).all()
    return render_template('products.html',
                         products=products,
                         is_admin=session.get('role') == 'admin',
                         session=session)

@app.route('/edit_product/<product_id>', methods=['POST'])
def edit_product(product_id):
    if session.get('role') != 'admin':
        flash('Hak Akses Tidak Cukup!', 'error')
        return redirect(url_for('products'))
    
    try:
        product = Product.query.filter_by(product_id=product_id).first()
        if product:
            product.name = request.form['name']
            product.specification = request.form['specification']
            product.price = float(request.form['price'])
            product.min_quantity = int(request.form['min_quantity'])
            product.supplier = request.form['supplier']
            
            db.session.commit()
            flash('Produk Berhasil Diperbarui!', 'success')
        else:
            flash('Produk Tidak Ditemukan!', 'error')
            
    except Exception as e:
        db.session.rollback()
        flash(f'Gagal: {str(e)}', 'error')
    
    return redirect(url_for('products'))

@app.route('/reports')
def reports():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # 只允许 admin 和 user 角色访问
    if session.get('role') not in ['admin', 'user']:
        flash('Hak Akses Tidak Cukup!', 'error')
        return redirect(url_for('dashboard'))
    
    # 获取查询参数
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    operation_type = request.args.get('operation_type')
    
    # 构建查询
    query = StockRecord.query.filter(StockRecord.operation_type != 'adjust').order_by(StockRecord.timestamp.desc())
    
    # 应用日期筛选
    if start_date:
        query = query.filter(StockRecord.timestamp >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        query = query.filter(StockRecord.timestamp <= datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1))
    
    # 应用操作类型筛选
    if operation_type:
        query = query.filter(StockRecord.operation_type == operation_type)
    
    # 获取记录
    records = query.all()
    
    # 计算统计摘要
    summary = {
        'in_count': StockRecord.query.filter_by(operation_type='in').count(),
        'in_quantity': sum(r.quantity for r in StockRecord.query.filter_by(operation_type='in').all()),
        'out_count': StockRecord.query.filter_by(operation_type='out').count(),
        'out_quantity': sum(r.quantity for r in StockRecord.query.filter_by(operation_type='out').all())
    }
    
    return render_template('reports.html',
                         records=records,
                         summary=summary,
                         is_admin=session.get('role') == 'admin',
                         session=session)

@app.route('/export_report')
def export_report():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if session.get('role') != 'admin':
        flash('Hak Akses Tidak Cukup!', 'error')
        return redirect(url_for('dashboard'))
    
    # 获取查询参数
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    operation_type = request.args.get('operation_type')
    
    # 构建查询
    query = StockRecord.query.filter(StockRecord.operation_type != 'adjust').order_by(StockRecord.timestamp.desc())
    
    # 应用日期筛选
    if start_date:
        query = query.filter(StockRecord.timestamp >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        query = query.filter(StockRecord.timestamp <= datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1))
    
    # 应用操作类型筛选
    if operation_type:
        query = query.filter(StockRecord.operation_type == operation_type)
    
    # 获取记录
    records = query.all()
    
    # 创建Excel工作表
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet('Laporan Stok')  # 改为"库存报表"的印尼语
    
    # 表头样式
    header_format = workbook.add_format({
        'bold': True,
        'align': 'center',
        'valign': 'vcenter',
        'bg_color': '#D9EAD3',
        'border': 1
    })
    
    # 添加数据样式
    data_format = workbook.add_format({
        'align': 'center',
        'valign': 'vcenter',
        'border': 1
    })
    
    # 写入表头（改为印尼语）
    headers = [
        'Waktu',           # 时间
        'Kode Produk',     # 商品ID
        'Nama Produk',     # 商品名称
        'Spesifikasi',     # 商品规格
        'Harga',           # 单价
        'Jenis Operasi',   # 操作类型
        'Tujuan',          # 出库去向
        'Jumlah',          # 数量
        'Operator'         # 操作员
    ]
    
    for col, header in enumerate(headers):
        worksheet.write(0, col, header, header_format)
    
    # 写入数据
    for row, record in enumerate(records, start=1):
        worksheet.write(row, 0, record.timestamp.strftime('%Y-%m-%d'), data_format)
        worksheet.write(row, 1, record.product_id, data_format)
        worksheet.write(row, 2, record.product.name if record.product else 'Produk Tidak Dikenal', data_format)
        worksheet.write(row, 3, record.product.specification if record.product and record.product.specification else '-', data_format)
        worksheet.write(row, 4, f'Rp {record.product.price:,.0f}' if record.product else '-', data_format)
        worksheet.write(row, 5, {
            'in': 'Barang Masuk',
            'out': 'Barang Keluar'
        }.get(record.operation_type, ''), data_format)
        worksheet.write(row, 6, 
            {
                'preprocessing': 'Ruang Pre-processing',
                'production': 'Ruang Produksi',
                'packaging': 'Ruang Pengemasan',
                'office': 'Kantor'
            }.get(record.destination, '-') if record.operation_type == 'out' else '-',
            data_format)
        worksheet.write(row, 7, record.quantity, data_format)
        worksheet.write(row, 8, record.operator.username, data_format)
    
    # 调整列宽
    worksheet.set_column('A:A', 12)  # 时间列
    worksheet.set_column('B:B', 15)  # 商品ID列
    worksheet.set_column('C:C', 20)  # 商品名称列
    worksheet.set_column('D:D', 15)  # 商品规格列
    worksheet.set_column('E:E', 15)  # 单价列
    worksheet.set_column('F:F', 10)  # 操作类型列
    worksheet.set_column('G:G', 15)  # 出库去向列
    worksheet.set_column('H:H', 10)  # 数量列
    worksheet.set_column('I:I', 15)  # 操作员列
    
    workbook.close()
    
    # 将指针移到文件开头
    output.seek(0)
    
    # 生成下载文件名（改为印尼语）
    filename = f'Laporan_Stok_{datetime.now().strftime("%Y%m%d")}.xlsx'
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )

@app.route('/search_product')
def search_product():
    if 'user_id' not in session:
        return jsonify([])
    
    name = request.args.get('name', '').strip()
    if not name:
        return jsonify([])
    
    # 使用 LIKE 进行模糊查询
    products = Product.query.filter(Product.name.like(f'%{name}%')).order_by(Product.product_id.asc()).all()
    
    # 转换为 JSON 格式
    result = [{
        'product_id': p.product_id,
        'name': p.name,
        'specification': p.specification,
        'price': p.price
    } for p in products]
    
    return jsonify(result)

@app.route('/get_product_name/<product_id>')
def get_product_name(product_id):
    if 'user_id' not in session:
        return jsonify({'name': '', 'specification': ''})
    
    product = Product.query.filter_by(product_id=product_id).first()
    return jsonify({
        'name': product.name if product else '',
        'specification': product.specification if product else ''
    })

def get_next_product_id():
    # 获取最后一个商品ID
    last_product = Product.query.order_by(Product.product_id.desc()).first()
    if not last_product:
        return '1001'  # 如果没有商品，从1001开始
    
    try:
        # 提取最后一个ID的数字部分并加1
        last_id = int(last_product.product_id)
        return str(last_id + 1)
    except ValueError:
        # 如果现有ID不是纯数字，从1001开始
        return '1001'

@app.route('/settings')
def settings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # 获取用户列表（仅管理员可见）
    users = User.query.all() if session.get('role') == 'admin' else []
    
    return render_template('settings.html',
                         users=users,
                         is_admin=session.get('role') == 'admin',
                         session=session)

@app.route('/change_password', methods=['POST'])
def change_password():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        user = User.query.get(session['user_id'])
        
        if not user.check_password(current_password):
            flash('当前密码错误！', 'error')
            return redirect(url_for('settings'))
        
        if new_password != confirm_password:
            flash('两次输入的新密码不一致！', 'error')
            return redirect(url_for('settings'))
        
        user.set_password(new_password)
        db.session.commit()
        flash('Perubahan Berhasil!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'密码修改失败：{str(e)}', 'error')
    
    return redirect(url_for('settings'))

@app.route('/add_user', methods=['POST'])
def add_user():
    if session.get('role') != 'admin':
        flash('权限不足！', 'error')
        return redirect(url_for('settings'))
    
    try:
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        
        if User.query.filter_by(username=username).first():
            flash('用户名已存在！', 'error')
            return redirect(url_for('settings'))
        
        user = User(username=username, role=role)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        flash('Pengguna Berhasil Ditambahkan!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'用户添加失败：{str(e)}', 'error')
    
    return redirect(url_for('settings'))

@app.route('/delete_user/<username>')
def delete_user(username):
    if session.get('role') != 'admin':
        flash('权限不足！', 'error')
        return redirect(url_for('settings'))
    
    if username == 'admin':
        flash('不能删除管理员账户！', 'error')
        return redirect(url_for('settings'))
    
    try:
        user = User.query.filter_by(username=username).first()
        if user:
            db.session.delete(user)
            db.session.commit()
            flash('Pengguna Berhasil Dihapus!', 'success')
        else:
            flash('用户不存在！', 'error')
            
    except Exception as e:
        db.session.rollback()
        flash(f'用户删除失败：{str(e)}', 'error')
    
    return redirect(url_for('settings'))

if __name__ == '__main__':
    # 修改主机地址为 0.0.0.0，允许外部访问
    # 修改端口为 5001（如果 5001 被占用，可以换成其他端口如 5002）
    app.run(host='0.0.0.0', port=5001, debug=True) 